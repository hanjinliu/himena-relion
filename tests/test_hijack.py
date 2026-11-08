import os
import threading
import time
import tomllib
from pathlib import Path

import mrcfile
import numpy as np
import polars as pl
import pytest
from himena import MainWindow
from himena.testing import choose_one_dialog_response
from qtpy import QtCore, QtGui, QtWidgets as QtW
from starfile_rs import as_star, read_star

from himena_relion import pipeline_watcher
from himena_relion._job_dir import JobDirectory
from himena_relion._pipeline import RelionDefaultPipeline
from himena_relion._widgets import QRelionJobWidget
from himena_relion._widgets._job_widgets import QJobParameterView
from himena_relion.consts import (
    DEFAULT_PIPELINE_STAR,
    NODES_DIR,
    FileNames,
    Plane,
    ProjectionMode,
)
from himena_relion.hijack import (
    USE_RELION_GUI,
    _base,
    find_hijacker,
    start_job,
    update_marker,
)
from himena_relion.hijack import select_interactive as _sel
from himena_relion.hijack._select_gui import (
    ClassImages,
    QClassSelectionJobWidget,
    QClassSelector,
    SortBy,
    _to_qimage,
)
from himena_relion.io import _impl
from himena_relion.relion5.widgets._select import QSelectInteractiveViewer
from himena_relion.schemas import RelionPipelineModel
from ._utils import JOBS_DIR_SPA

SELECT_JOB = "Select/job010/"
IMPORT_PATH = "himena_relion.hijack.select_interactive:SelectClassesInteractive"
# number of particles in each class (class 3 is empty)
CLASS_SIZES = [12, 30, 0, 18, 6]


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, newline="\n")


def _pipeline_text(
    classify_job: str,
    outputs: list[tuple[str, str]],
    status: str,
    with_classify_process: bool = True,
):
    lines = [
        "\n# version 50001\n\ndata_pipeline_general\n\n_rlnPipeLineJobCounter 11\n",
        "\n# version 50001\n\ndata_pipeline_processes\n\nloop_",
        "_rlnPipeLineProcessName #1",
        "_rlnPipeLineProcessAlias #2",
        "_rlnPipeLineProcessTypeLabel #3",
        "_rlnPipeLineProcessStatusLabel #4",
    ]
    if with_classify_process:
        lines.append(f"{classify_job} None relion.class2d Succeeded")
    lines.append(f"{SELECT_JOB} None relion.select.interactive {status}")
    lines += [
        "\n# version 50001\n\ndata_pipeline_nodes\n\nloop_",
        "_rlnPipeLineNodeName #1",
        "_rlnPipeLineNodeTypeLabel #2",
        "_rlnPipeLineNodeTypeLabelDepth #3",
        f"{classify_job}run_it025_optimiser.star OptimiserData.star.relion.class2d 1",
    ]
    lines += [f"{SELECT_JOB}{name} {label} 1" for name, label in outputs]
    lines += [
        "\n# version 50001\n\ndata_pipeline_input_edges\n\nloop_",
        "_rlnPipeLineEdgeFromNode #1",
        "_rlnPipeLineEdgeProcess #2",
        f"{classify_job}run_it025_optimiser.star {SELECT_JOB}",
        "\n# version 50001\n\ndata_pipeline_output_edges\n\nloop_",
        "_rlnPipeLineEdgeProcess #1",
        "_rlnPipeLineEdgeToNode #2",
    ]
    lines += [f"{SELECT_JOB} {SELECT_JOB}{name}" for name, _ in outputs]
    return "\n".join(lines) + "\n"


def _make_project(
    root: Path,
    is_3d: bool = False,
    job_params: dict[str, str] | None = None,
) -> JobDirectory:
    """Create a RELION project with a finished classification job and a scheduled
    Select job, as created by `relion_pipeliner --addJobFromStar`."""
    rng = np.random.default_rng(1234)
    n_classes = len(CLASS_SIZES)
    classify_job = "Class3D/job009/" if is_3d else "Class2D/job009/"
    cdir = root / classify_job
    cdir.mkdir(parents=True)
    if is_3d:
        refs = []
        for i in range(n_classes):
            path = cdir / f"run_it025_class{i + 1:03d}.mrc"
            with mrcfile.new(path) as mrc:
                mrc.set_data(rng.normal(size=(12, 12, 12)).astype(np.float32))
                mrc.voxel_size = 2.0
            refs.append(f"{classify_job}{path.name}")
    else:
        with mrcfile.new(cdir / "run_it025_classes.mrcs") as mrc:
            data = rng.normal(size=(n_classes, 16, 16)).astype(np.float32)
            mrc.set_data(data)
            mrc.set_image_stack()
            mrc.voxel_size = 2.0
        refs = [
            f"{i + 1:06d}@{classify_job}run_it025_classes.mrcs"
            for i in range(n_classes)
        ]
    total = sum(CLASS_SIZES)
    df_classes = pl.DataFrame(
        {
            "rlnReferenceImage": refs,
            "rlnClassDistribution": [n / total for n in CLASS_SIZES],
            "rlnAccuracyRotations": [1.5] * n_classes,
            "rlnEstimatedResolution": [8.0, 6.5, 999.0, 7.2, 12.0],
        }
    )
    df_groups = pl.DataFrame(
        {
            "rlnGroupNumber": [1, 2, 3, 4],
            "rlnGroupName": ["g1", "g2", "g3", "g4"],
            "rlnGroupNrParticles": [10, 10, 10, 10],
            "rlnGroupScaleCorrection": [1.2, 0.8, 1.0, 0.9],
        }
    )
    _write(
        cdir / "run_it025_model.star",
        as_star(
            {
                "model_general": {"rlnReferenceDimensionality": 3 if is_3d else 2},
                "model_classes": df_classes,
                "model_groups": df_groups,
            }
        ).to_string(),
    )
    _write(
        cdir / "run_it025_optimiser.star",
        "\n# version 50001\n\ndata_optimiser_general\n\n"
        f"_rlnOutputRootName {classify_job}run\n"
        f"_rlnModelStarFile {classify_job}run_it025_model.star\n"
        f"_rlnExperimentalDataStarFile {classify_job}run_it025_data.star\n",
    )
    rows = []
    iptcl = 0
    for icls, size in enumerate(CLASS_SIZES):
        for _ in range(size):
            iptcl += 1
            rows.append(
                f"{iptcl:06d}@Extract/job008/Movies/mic.mrcs  {icls + 1}  "
                f'{iptcl % 4 + 1}  1  4.084572e+05  -1.2345e-07  ""'
            )
    # shuffle so that particles of the same class are not contiguous
    order = rng.permutation(len(rows))
    _write(
        cdir / "run_it025_data.star",
        "\n# version 50001\n\ndata_optics\n\nloop_\n_rlnOpticsGroup #1\n"
        "_rlnOpticsGroupName #2\n_rlnImagePixelSize #3\n1 opticsGroup1 2.000000\n\n"
        "\n# version 50001\n\ndata_particles\n\nloop_\n_rlnImageName #1\n"
        "_rlnClassNumber #2\n_rlnGroupNumber #3\n_rlnOpticsGroup #4\n"
        "_rlnLogLikeliContribution #5\n_rlnMaxValueProbDistribution #6\n"
        "_rlnMicrographOriginalName #7\n" + "\n".join(rows[i] for i in order) + "\n",
    )
    cdir.joinpath(FileNames.EXIT_SUCCESS).touch()

    # Select job, as created by relion_pipeliner --addJobFromStar
    job_star = (JOBS_DIR_SPA / "Select" / "job001" / "job.star").read_text()
    params = {"fn_model": f"{classify_job}run_it025_optimiser.star"}
    params.update(job_params or {})
    lines = []
    for line in job_star.splitlines():
        key = line.strip().split(" ")[0]
        if key in params:
            line = f"{key} {params[key]}"
        lines.append(line)
    sdir = root / SELECT_JOB
    sdir.mkdir(parents=True)
    _write(sdir / "job.star", "\n".join(lines) + "\n")
    outputs = [("particles.star", "ParticleGroupMetadata.star.relion")]
    if not is_3d:
        outputs.append(
            ("class_averages.star", "Image2DGroupMetadata.star.relion.classaverages")
        )
    _write(
        root / DEFAULT_PIPELINE_STAR,
        _pipeline_text(classify_job, outputs, "Scheduled"),
    )
    _write(
        sdir / "job_pipeline.star",
        _pipeline_text(classify_job, outputs, "Scheduled", with_classify_process=False),
    )
    _write(
        sdir / DEFAULT_PIPELINE_STAR, _pipeline_text(classify_job, outputs, "Scheduled")
    )
    (sdir / "note.txt").write_text("")
    return JobDirectory(sdir)


def _status(rln_dir: Path, job_id: str = SELECT_JOB) -> str:
    pipeline = RelionPipelineModel.validate_file(rln_dir / DEFAULT_PIPELINE_STAR)
    is_job = pipeline.processes.process_name == job_id
    return pipeline.processes.status_label.filter(is_job)[0]


def _load(job_dir: JobDirectory) -> _sel.ClassSelectionInput:
    return _sel.ClassSelectionInput.from_fn_model(
        job_dir.get_job_param("fn_model"), job_dir.relion_project_dir
    )


@pytest.fixture
def in_project(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def no_relion(monkeypatch):
    """Fail if relion_pipeliner is executed."""
    calls = []

    def _popen(args, *_, **__):
        calls.append(args)
        raise AssertionError(f"relion_pipeliner should not be called: {args}")

    monkeypatch.setattr(pipeline_watcher.subprocess, "Popen", _popen)
    return calls


### Input and output files ###


def test_find_hijacker(tmp_path: Path):
    job_dir = _make_project(tmp_path)
    assert find_hijacker(job_dir) is _sel.SelectClassesInteractive
    # not hijacked if fn_model is not given (selection of micrographs/particles)
    job_dir.job_star().write_text(
        job_dir.job_star()
        .read_text()
        .replace("Class2D/job009/run_it025_optimiser.star", '""')
    )
    assert find_hijacker(job_dir) is None
    # not hijacked for other job types
    other = tmp_path / "Select" / "job011"
    other.mkdir()
    other.joinpath("job.star").write_text(
        (JOBS_DIR_SPA / "Select" / "job002" / "job.star").read_text()
    )
    assert find_hijacker(JobDirectory(other)) is None


@pytest.mark.parametrize("is_3d", [False, True])
def test_selection_params(tmp_path: Path, is_3d: bool):
    job_dir = _make_project(
        tmp_path,
        is_3d=is_3d,
        job_params={"do_recenter": "Yes", "do_regroup": "Yes", "nr_groups": "3"},
    )
    params = _sel.SelectionParams.from_job_dir(job_dir)
    assert params.fn_model == job_dir.get_job_param("fn_model")
    assert params.write_class_averages == (not is_3d)
    assert params.do_recenter == (not is_3d)  # only for 2D, same as RELION
    assert params.nr_regroups == 3


@pytest.mark.parametrize("is_3d", [False, True])
def test_load_input(tmp_path: Path, is_3d: bool):
    job_dir = _make_project(tmp_path, is_3d=is_3d)
    source = _load(job_dir)
    assert source.num_classes == 5
    assert source.num_particles == sum(CLASS_SIZES)
    assert source.class_numbers.tolist() == [1, 2, 3, 4, 5]
    assert source.particle_counts().tolist() == CLASS_SIZES
    assert source.is_3d() == is_3d
    images = list(source.iter_class_images())
    assert len(images) == 5
    assert all(img.ndim == (3 if is_3d else 2) for img in images)
    fn_model = job_dir.get_job_param("fn_model")
    assert _sel.expects_class_averages(job_dir, fn_model) == (not is_3d)


def test_write_selection_2d(tmp_path: Path):
    job_dir = _make_project(tmp_path)
    source = _load(job_dir)
    selected = np.array([True, False, False, True, False])
    result = _sel.write_selection(
        job_dir, source, selected, write_class_averages=True, log=lambda _: None
    )
    assert result.num_classes == 2
    assert result.num_particles == 12 + 18

    backup = read_star(job_dir.path / "backup_selection.star").first().trust_loop()
    assert backup.to_polars()["rlnSelected"].to_list() == [1, 0, 0, 1, 0]
    assert _sel.read_backup_selection(job_dir, 5).tolist() == selected.tolist()

    cls_avg = read_star(job_dir.path / "class_averages.star").first().trust_loop()
    df_cls = cls_avg.to_polars()
    assert df_cls["rlnClassNumber"].to_list() == [1, 4]
    assert df_cls["rlnReferenceImage"].to_list() == [
        "000001@Class2D/job009/run_it025_classes.mrcs",
        "000004@Class2D/job009/run_it025_classes.mrcs",
    ]

    star = read_star(job_dir.path / "particles.star")
    assert list(star.keys()) == ["optics", "particles"]
    df = star["particles"].trust_loop().to_polars()
    assert df.height == 30
    assert set(df["rlnClassNumber"].to_list()) == {1, 4}
    # values are written as they were
    text = (job_dir.path / "particles.star").read_text()
    assert "4.084572e+05" in text
    assert "-1.2345e-07" in text
    assert '""' in text
    # the original order is kept
    df_all = source.particles.filter(pl.col("rlnClassNumber").is_in([1, 4]))
    assert df["rlnImageName"].to_list() == df_all["rlnImageName"].to_list()

    with pytest.raises(ValueError):  # nothing selected
        _sel.write_selection(
            job_dir, source, np.zeros(5, dtype=bool), write_class_averages=True
        )
    with pytest.raises(ValueError):  # no particles in the selected classes
        _sel.write_selection(
            job_dir,
            source,
            np.array([0, 0, 1, 0, 0], dtype=bool),
            write_class_averages=True,
        )


def test_write_selection_3d(tmp_path: Path):
    job_dir = _make_project(tmp_path, is_3d=True)
    source = _load(job_dir)
    _sel.write_selection(
        job_dir,
        source,
        np.array([0, 1, 0, 0, 1], dtype=bool),
        write_class_averages=False,
        log=lambda _: None,
    )
    assert not job_dir.path.joinpath("class_averages.star").exists()
    df = (
        read_star(job_dir.path / "particles.star")["particles"].trust_loop().to_polars()
    )
    assert df.height == 30 + 6


def test_recenter(tmp_path: Path):
    img = np.zeros((16, 16), dtype=np.float32)
    img[2:5, 10:13] = 1.0  # center of mass at (3, 11)
    out = _sel.recenter_image(img)
    yy, xx = np.indices(out.shape)
    pos = out > 0
    assert np.average(yy[pos], weights=out[pos]) == pytest.approx(8, abs=0.1)
    assert np.average(xx[pos], weights=out[pos]) == pytest.approx(8, abs=0.1)

    job_dir = _make_project(tmp_path)
    source = _load(job_dir)
    _sel.write_selection(
        job_dir,
        source,
        np.array([0, 1, 0, 1, 1], dtype=bool),
        write_class_averages=True,
        do_recenter=True,
        log=lambda _: None,
    )
    df_cls = (
        read_star(job_dir.path / "class_averages.star").first().trust_loop().to_polars()
    )
    assert df_cls["rlnReferenceImage"].to_list() == [
        f"{i:06d}@Select/job010/class_averages.mrcs" for i in [1, 2, 3]
    ]
    with mrcfile.open(job_dir.path / "class_averages.mrcs") as mrc:
        assert mrc.data.shape == (3, 16, 16)
        assert mrc.voxel_size.x == pytest.approx(2.0)


def test_regroup():
    particles = pl.DataFrame(
        {
            "rlnImageName": [f"{i}@a.mrcs" for i in range(40)],
            "rlnGroupNumber": [1] * 10 + [2] * 10 + [3] * 10 + [4] * 10,
            "rlnOpticsGroup": [1] * 40,
        }
    )
    groups = pl.DataFrame(
        {
            "rlnGroupNumber": [1, 2, 3, 4],
            "rlnGroupScaleCorrection": [1.2, 0.8, 1.0, 0.9],
        }
    )
    out = _sel.regroup_particles(particles, groups, 2, log=lambda _: None)
    assert "rlnGroupNumber" not in out.columns
    # sorted by scale: 2 (0.8), 4 (0.9), 3 (1.0), 1 (1.2). Average size is 20, and a
    # new group starts when the accumulated size exceeds 20 (same as RELION).
    name_map = dict(zip(particles["rlnGroupNumber"], out["rlnGroupName"]))
    assert name_map == {2: "group_1", 4: "group_1", 3: "group_2", 1: "group_2"}
    with pytest.raises(ValueError):
        _sel.regroup_particles(particles, groups, 5, log=lambda _: None)


### GUI ###


def test_class_selector(qtbot, tmp_path: Path):
    job_dir = _make_project(tmp_path)
    source = _load(job_dir)
    images = [ClassImages(img) for img in source.iter_class_images()]
    initial = np.array([False, True, False, False, True])
    selector = QClassSelector(source, images, initial=initial)
    qtbot.addWidget(selector)
    assert selector.selection().tolist() == initial.tolist()
    # default: sorted by the class number
    assert selector.display_order().tolist() == [0, 1, 2, 3, 4]
    selector.sort_by(SortBy.PARTICLES)
    assert selector.display_order().tolist() == [1, 3, 0, 4, 2]
    selector.sort_by(SortBy.RESOLUTION)
    assert selector.display_order().tolist() == [1, 3, 0, 4, 2]
    assert selector.selection().tolist() == initial.tolist()  # kept after sorting
    selector.sort_by(SortBy.CLASS_NUMBER)
    assert selector.display_order().tolist() == [0, 1, 2, 3, 4]

    # toggle by clicking
    view = selector._view
    selector.show()
    qtbot.waitExposed(selector)
    rect = view.visualRect(selector._model.index(0))
    qtbot.mouseClick(
        view.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=rect.center()
    )
    assert selector.selection().tolist() == [True, True, False, False, True]
    qtbot.mouseClick(
        view.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=rect.center()
    )
    assert selector.selection().tolist() == initial.tolist()

    selector.invert_selection()
    assert selector.selection().tolist() == [True, False, True, True, False]
    selector._select_range(3, 5)
    assert selector.selection().tolist() == [True, False, True, True, True]
    selector.clear_selection()
    assert not selector.selection().any()
    selector.select_all()
    assert selector.selection().all()
    with qtbot.waitSignal(selector.save_requested, timeout=1000):
        selector._save_btn.click()


def test_class_selector_cursor(qtbot, tmp_path: Path):
    job_dir = _make_project(tmp_path)
    source = _load(job_dir)
    images = [ClassImages(img) for img in source.iter_class_images()]
    selector = QClassSelector(source, images)
    qtbot.addWidget(selector)
    selector.resize(900, 600)
    selector.show()
    qtbot.waitExposed(selector)
    view = selector._view
    viewport = view.viewport()

    def _move_to(pos: QtCore.QPoint):
        # QTest.mouseMove moves the real cursor, which does not reach a window in
        # the background. Send the event directly.
        event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove,
            QtCore.QPointF(pos),
            QtCore.QPointF(viewport.mapToGlobal(pos)),
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
        )
        QtW.QApplication.sendEvent(viewport, event)

    _move_to(view.visualRect(selector._model.index(0)).center())
    assert viewport.cursor().shape() == QtCore.Qt.CursorShape.PointingHandCursor
    empty_pos = QtCore.QPoint(viewport.width() - 5, viewport.height() - 5)
    assert not view.indexAt(empty_pos).isValid()
    _move_to(empty_pos)
    assert viewport.cursor().shape() == QtCore.Qt.CursorShape.ArrowCursor


def test_class_selector_3d(qtbot, tmp_path: Path):
    job_dir = _make_project(tmp_path, is_3d=True)
    source = _load(job_dir)
    images = [ClassImages(img) for img in source.iter_class_images()]
    selector = QClassSelector(source, images)
    qtbot.addWidget(selector)
    for plane in Plane:
        for proj in ProjectionMode:
            selector._plane_mgui.value = plane
            selector._projection_mgui.value = proj
            shown = selector._model.index(0).data(QtCore.Qt.ItemDataRole.DecorationRole)
            assert shown == _to_qimage(images[0].get(plane, proj))
    selector._size_slider.setValue(200)
    assert not selector._view_options.isHidden()


### Pipeline ###


def test_update_marker(tmp_path: Path):
    job_dir = _make_project(tmp_path)
    marker = job_dir.path / FileNames.USE_HIMENA_IMPL
    assert update_marker(job_dir) is _sel.SelectClassesInteractive
    # TOML format, so that more fields can be added in the future
    assert tomllib.loads(marker.read_text()) == {"himena_class": IMPORT_PATH}
    assert _base.read_marker(job_dir) == {"himena_class": IMPORT_PATH}
    assert _base.marked_hijacker(job_dir) is _sel.SelectClassesInteractive
    assert not marker.with_name(marker.name + ".tmp").exists()

    # broken file: fall back to the job type
    marker.write_text("himena_class = ")
    assert _base.read_marker(job_dir) == {}
    assert _base.marked_hijacker(job_dir) is _sel.SelectClassesInteractive
    update_marker(job_dir)
    # the marker is removed if the job cannot be hijacked any more
    job_dir.job_star().write_text(
        job_dir.job_star()
        .read_text()
        .replace("Class2D/job009/run_it025_optimiser.star", '""')
    )
    assert update_marker(job_dir) is None
    assert not marker.exists()


def test_update_marker_use_relion_gui(tmp_path: Path):
    job_dir = _make_project(tmp_path)
    marker = job_dir.path / FileNames.USE_HIMENA_IMPL
    job_star_text = job_dir.job_star().read_text()
    update_marker(job_dir)
    assert marker.exists()
    assert _base.job_params_with_marker(job_dir)[USE_RELION_GUI] == "No"
    # "Use RELION GUI" removes the marker, so the job is run by RELION
    assert update_marker(job_dir, use_relion_gui=True) is None
    assert not marker.exists()
    assert _base.job_params_with_marker(job_dir)[USE_RELION_GUI] == "Yes"
    # the parameter is not in job.star
    assert job_dir.job_star().read_text() == job_star_text
    assert USE_RELION_GUI not in job_dir.get_job_params_as_dict()


def test_job_params_with_marker_other_jobs():
    # jobs that cannot be hijacked do not have the parameter
    job_dir = JobDirectory(JOBS_DIR_SPA / "Refine3D" / "job001")
    params = _base.job_params_with_marker(job_dir)
    assert params == job_dir.get_job_params_as_dict()
    assert USE_RELION_GUI not in params


def test_execute_marked_job(in_project: Path, no_relion):
    job_dir = _make_project(in_project)
    update_marker(job_dir)
    job_dir.path.joinpath(FileNames.EXIT_FAILURE).touch()  # from the previous run
    assert job_dir.is_scheduled()

    assert pipeline_watcher.execute_job(SELECT_JOB, cwd=in_project) is None
    assert no_relion == []
    assert _status(in_project) == "Running"
    assert not job_dir.path.joinpath(FileNames.EXIT_FAILURE).exists()
    assert job_dir.state().name == "RUNNING"
    assert not job_dir.is_scheduled()
    job_pipeline = RelionPipelineModel.validate_file(job_dir.job_pipeline())
    assert job_pipeline.processes.status_label[0] == "Running"
    assert "himena-relion main window" in job_dir.path.joinpath("note.txt").read_text()
    assert _base.running_hijacker(job_dir) is _sel.SelectClassesInteractive
    # run.out and run.err are created as RELION does
    assert job_dir.path.joinpath("run.out").exists()
    assert job_dir.path.joinpath("run.err").exists()


def test_start_job_keeps_previous_logs(in_project: Path):
    job_dir = _make_project(in_project)
    update_marker(job_dir)
    job_dir.path.joinpath("run.out").write_text("previous out\n")
    job_dir.path.joinpath("run.err").write_text("previous err\n")
    start_job(job_dir)
    assert job_dir.path.joinpath("run.out").read_text() == "previous out\n"
    assert job_dir.path.joinpath("run.err").read_text() == "previous err\n"


def test_watcher_leaves_marked_job(in_project: Path, no_relion):
    job_dir = _make_project(in_project)
    update_marker(job_dir)
    watcher = pipeline_watcher.RelionPipelineWatcher(in_project)
    pipeline = RelionDefaultPipeline.from_pipeline_star(
        in_project / DEFAULT_PIPELINE_STAR
    )
    watcher._on_job_state_changed(pipeline)
    assert no_relion == []
    assert _status(in_project) == "Running"


def _record_popen(monkeypatch) -> list[list[str]]:
    calls = []

    class _Proc:
        pid = 0

    monkeypatch.setattr(
        pipeline_watcher.subprocess,
        "Popen",
        lambda args, **_: calls.append(args) or _Proc(),
    )
    return calls


def _write_marker_later(job_dir: JobDirectory, delay: float = 0.2):
    timer = threading.Timer(
        delay, lambda: _base.write_marker(job_dir, {"himena_class": IMPORT_PATH})
    )
    timer.start()
    return timer


def test_watcher_runs_unmarked_job_with_relion(in_project: Path, monkeypatch):
    _make_project(in_project)
    calls = _record_popen(monkeypatch)
    t0 = time.monotonic()
    # the marker is not waited for, because `found_at` is not given
    pipeline_watcher.execute_job(SELECT_JOB, cwd=in_project)
    assert time.monotonic() - t0 < 0.5
    assert len(calls) == 1
    assert "--RunJobs" in calls[0]


def test_watcher_waits_for_marker_of_new_job(in_project: Path, no_relion, monkeypatch):
    # The job is added while the watcher is running. The main window writes the
    # marker after relion_pipeliner added the job.
    monkeypatch.setattr(_base, "_MARKER_GRACE_SEC", 3.0)
    job_dir = _make_project(in_project)
    watcher = pipeline_watcher.RelionPipelineWatcher(in_project)
    pipeline = RelionDefaultPipeline.from_pipeline_star(
        in_project / DEFAULT_PIPELINE_STAR
    )
    timer = _write_marker_later(job_dir)
    watcher._on_job_state_changed(pipeline)
    timer.join()
    assert no_relion == []
    assert _status(in_project) == "Running"


def test_watcher_does_not_wait_for_old_job(in_project: Path, monkeypatch):
    monkeypatch.setattr(_base, "_MARKER_GRACE_SEC", 60.0)
    _make_project(in_project)
    calls = _record_popen(monkeypatch)
    watcher = pipeline_watcher.RelionPipelineWatcher(in_project)
    # the job was found long ago (e.g. it was waiting for the parent job)
    watcher._found_at[SELECT_JOB.rstrip("/")] = time.monotonic() - 120
    pipeline = RelionDefaultPipeline.from_pipeline_star(
        in_project / DEFAULT_PIPELINE_STAR
    )
    t0 = time.monotonic()
    watcher._on_job_state_changed(pipeline)
    assert time.monotonic() - t0 < 5.0
    assert len(calls) == 1
    assert "--RunJobs" in calls[0]


def test_wait_for_marker(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(_base, "_MARKER_GRACE_SEC", 1.0)
    job_dir = _make_project(tmp_path)
    marker = job_dir.path / FileNames.USE_HIMENA_IMPL

    # the main window writes the marker shortly after the watcher found the job
    timer = _write_marker_later(job_dir)
    assert _base.wait_for_marker(job_dir, found_at=time.monotonic())
    timer.join()

    # no marker: wait until the end of the grace period
    marker.unlink()
    t0 = time.monotonic()
    assert not _base.wait_for_marker(job_dir, found_at=t0)
    assert time.monotonic() - t0 >= 0.9

    # found long ago, or not found by the watcher: no need to wait
    t0 = time.monotonic()
    assert not _base.wait_for_marker(job_dir, found_at=t0 - 60)
    assert not _base.wait_for_marker(job_dir)
    assert time.monotonic() - t0 < 0.5


def test_wait_for_marker_ignores_file_time(tmp_path: Path, monkeypatch):
    # The clock of the file server (e.g. NFS) may be different from that of this
    # machine, so that a job just added may look old.
    monkeypatch.setattr(_base, "_MARKER_GRACE_SEC", 3.0)
    job_dir = _make_project(tmp_path)
    old = time.time() - 3600
    os.utime(job_dir.job_star(), (old, old))
    timer = _write_marker_later(job_dir)
    assert _base.wait_for_marker(job_dir, found_at=time.monotonic())
    timer.join()


def test_wait_for_marker_before_job_star(tmp_path: Path, monkeypatch):
    # job.star may not be readable yet when the watcher found the job
    monkeypatch.setattr(_base, "_MARKER_GRACE_SEC", 3.0)
    job_dir = _make_project(tmp_path)
    job_star = job_dir.job_star()
    backup = job_star.with_name("job.star.bak")
    job_star.rename(backup)
    timer = threading.Timer(0.2, lambda: backup.rename(job_star))
    timer.start()
    timer_marker = _write_marker_later(job_dir, delay=0.5)
    assert _base.wait_for_marker(job_dir, found_at=time.monotonic())
    timer.join()
    timer_marker.join()


def test_wait_for_marker_not_hijacked(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(_base, "_MARKER_GRACE_SEC", 60.0)
    job_dir = _make_project(tmp_path)
    job_dir.job_star().write_text(
        job_dir.job_star()
        .read_text()
        .replace("Class2D/job009/run_it025_optimiser.star", '""')
    )
    t0 = time.monotonic()
    assert not _base.wait_for_marker(job_dir, found_at=t0)
    assert time.monotonic() - t0 < 0.5


def test_finish_job(in_project: Path):
    job_dir = _make_project(in_project)
    update_marker(job_dir)
    start_job(job_dir)
    _base.finish_job(job_dir, "Succeeded")
    assert job_dir.state().name == "EXIT_SUCCESS"
    assert _status(in_project) == "Succeeded"
    assert _base.running_hijacker(job_dir) is None


### Main window ###


def _job_widget(ui: MainWindow, job_dir: JobDirectory) -> QRelionJobWidget:
    for window in ui.iter_windows():
        widget = window.widget
        if isinstance(widget, QRelionJobWidget) and widget._job_dir is not None:
            if widget._job_dir.path == job_dir.path:
                return widget
    raise AssertionError(f"Job window of {job_dir.path} not found")


def test_results_tab_switches(himena_ui: MainWindow, in_project: Path, qtbot):
    job_dir = _make_project(in_project)
    update_marker(job_dir)

    # scheduled: the normal results viewer
    himena_ui.read_file(job_dir.job_star())
    widget = _job_widget(himena_ui, job_dir)
    assert isinstance(widget._results_widget, QSelectInteractiveViewer)

    # running: the class selection GUI
    start_job(job_dir)
    widget.refresh_results_widget()
    results = widget._results_widget
    assert isinstance(results, QClassSelectionJobWidget)
    assert widget._tab_widget.widget(0) is results
    qtbot.waitUntil(lambda: results.selector() is not None, timeout=5000)
    results.selector().set_selection(np.array([1, 1, 0, 0, 0], dtype=bool))
    assert results.save()

    # finished: back to the results viewer
    assert job_dir.state().name == "EXIT_SUCCESS"
    assert _status(in_project) == "Succeeded"
    for name, label in [
        ("particles.star", "ParticleGroupMetadata"),
        ("class_averages.star", "Image2DGroupMetadata"),
    ]:
        assert job_dir.path.joinpath(name).exists()
        assert in_project.joinpath(NODES_DIR, label, SELECT_JOB, name).exists()
    assert "selected particles" in job_dir.path.joinpath("run.out").read_text()
    assert isinstance(widget._results_widget, QSelectInteractiveViewer)
    assert widget._tab_widget.widget(0) is widget._results_widget

    # continue: the previous selection is loaded
    update_marker(job_dir)
    start_job(job_dir)
    widget.refresh_results_widget()
    results = widget._results_widget
    assert isinstance(results, QClassSelectionJobWidget)
    qtbot.waitUntil(lambda: results.selector() is not None, timeout=5000)
    assert results.selector().selection().tolist() == [True, True, False, False, False]


def test_save_without_selection(
    himena_ui: MainWindow, in_project: Path, qtbot, monkeypatch
):
    job_dir = _make_project(in_project)
    update_marker(job_dir)
    start_job(job_dir)
    himena_ui.read_file(job_dir.job_star())
    results = _job_widget(himena_ui, job_dir)._results_widget
    assert isinstance(results, QClassSelectionJobWidget)
    qtbot.waitUntil(lambda: results.selector() is not None, timeout=5000)
    monkeypatch.setattr(QtW.QMessageBox, "warning", lambda *_, **__: None)
    assert not results.save()
    assert _status(in_project) == "Running"


def test_load_failure_is_shown(himena_ui: MainWindow, in_project: Path):
    job_dir = _make_project(in_project)
    in_project.joinpath("Class2D/job009/run_it025_data.star").unlink()
    update_marker(job_dir)
    start_job(job_dir)
    results = QClassSelectionJobWidget(job_dir)
    results.initialize(job_dir)
    assert results.selector() is None
    assert "Failed to load" in results._message.text()
    err = job_dir.path.joinpath("run.err").read_text()
    assert "Traceback" in err
    assert "run_it025_data.star" in err


def test_save_failure_is_logged(
    himena_ui: MainWindow, in_project: Path, qtbot, monkeypatch
):
    job_dir = _make_project(in_project)
    update_marker(job_dir)
    start_job(job_dir)
    results = QClassSelectionJobWidget(job_dir)
    results.initialize(job_dir)
    qtbot.waitUntil(lambda: results.selector() is not None, timeout=5000)
    results.selector().set_selection(np.array([0, 0, 1, 0, 0], dtype=bool))  # empty
    monkeypatch.setattr(QtW.QMessageBox, "critical", lambda *_, **__: None)
    assert not results.save()
    assert (
        "do not contain any particles" in job_dir.path.joinpath("run.err").read_text()
    )
    assert _status(in_project) == "Running"


def test_abort_marked_job(himena_ui: MainWindow, in_project: Path):
    job_dir = _make_project(in_project)
    update_marker(job_dir)
    start_job(job_dir)
    with choose_one_dialog_response(himena_ui, True):
        _impl.abort_relion_job(himena_ui, job_dir)
    assert job_dir.state().name == "EXIT_ABORTED"
    assert _status(in_project) == "Aborted"


def test_flowchart_opens_started_job(himena_ui: MainWindow, in_project: Path):
    from himena_relion.pipeline.widgets import QRelionPipelineFlowChart

    job_dir = _make_project(in_project)
    update_marker(job_dir)
    himena_ui.read_file(in_project / DEFAULT_PIPELINE_STAR)
    for dock in himena_ui.dock_widgets:
        if isinstance(flowchart := dock.widget, QRelionPipelineFlowChart):
            break
    else:
        raise AssertionError("flowchart not found")
    with pytest.raises(AssertionError):
        _job_widget(himena_ui, job_dir)

    start_job(job_dir)
    flowchart._on_job_state_changed(
        RelionDefaultPipeline.from_pipeline_star(in_project / DEFAULT_PIPELINE_STAR)
    )
    widget = _job_widget(himena_ui, job_dir)
    assert isinstance(widget._results_widget, QClassSelectionJobWidget)


@pytest.mark.parametrize("use_relion_gui", [False, True])
def test_create_job_writes_marker(
    himena_ui: MainWindow, in_project: Path, monkeypatch, use_relion_gui: bool
):
    from himena_relion import _job_class
    from himena_relion.relion5._builtins import SelectClassesInteractiveJob

    job_dir = _make_project(in_project)
    # relion_pipeliner already created the job directory (see _make_project)
    monkeypatch.setattr(
        _job_class, "_run_relion_pipeliner_add_job_from_star", lambda *_, **__: None
    )
    watcher_started = []
    monkeypatch.setattr(
        _job_class,
        "run_watcher_new_process",
        lambda *_: watcher_started.append(
            job_dir.path.joinpath(FileNames.USE_HIMENA_IMPL).exists()
        ),
    )
    SelectClassesInteractiveJob.create_job(
        fn_model="Class2D/job009/run_it025_optimiser.star",
        use_relion_gui=use_relion_gui,
        _cwd=in_project,
    )
    # the marker must be written before the watcher starts, and only when the job is
    # not run by RELION GUI
    assert watcher_started == [not use_relion_gui]


def test_create_job_stops_outdated_watcher(
    himena_ui: MainWindow, in_project: Path, monkeypatch
):
    from himena_relion import _job_class
    from himena_relion.relion5._builtins import SelectClassesInteractiveJob

    _make_project(in_project)
    calls = []
    monkeypatch.setattr(
        _job_class, "stop_outdated_watcher", lambda *_: calls.append("stop") or True
    )
    monkeypatch.setattr(
        _job_class,
        "_run_relion_pipeliner_add_job_from_star",
        lambda *_, **__: calls.append("add"),
    )
    monkeypatch.setattr(
        _job_class, "run_watcher_new_process", lambda *_: calls.append("start")
    )
    fn_model = "Class2D/job009/run_it025_optimiser.star"
    # an outdated watcher would run the new job in its own way
    SelectClassesInteractiveJob.create_job(fn_model=fn_model, _cwd=in_project)
    assert calls == ["stop", "add", "start"]

    # the jobs handled by the stopped watcher must be run even if the job could not
    # be added
    def _fail(*_, **__):
        raise RuntimeError("relion_pipeliner failed")

    calls.clear()
    monkeypatch.setattr(_job_class, "_run_relion_pipeliner_add_job_from_star", _fail)
    with pytest.raises(RuntimeError):
        SelectClassesInteractiveJob.create_job(fn_model=fn_model, _cwd=in_project)
    assert calls == ["stop", "start"]


@pytest.mark.parametrize("use_relion_gui", [False, True])
def test_overwrite_and_continue_use_relion_gui(
    himena_ui: MainWindow, in_project: Path, monkeypatch, use_relion_gui: bool
):
    from himena_relion import _job_class
    from himena_relion.relion5._builtins import SelectClassesInteractiveJob
    from himena_relion.relion5._continues import SelectClassesInteractiveContinue

    monkeypatch.setattr(_job_class, "run_watcher_new_process", lambda *_: None)
    job_dir = _make_project(in_project)
    marker = job_dir.path / FileNames.USE_HIMENA_IMPL

    # overwrite: start from the opposite state
    update_marker(job_dir, use_relion_gui=not use_relion_gui)
    SelectClassesInteractiveJob(job_dir).edit_and_run_job(
        fn_model="Class2D/job009/run_it025_optimiser.star",
        use_relion_gui=use_relion_gui,
    )
    assert marker.exists() is (not use_relion_gui)
    assert USE_RELION_GUI not in job_dir.get_job_params_as_dict()

    # continue
    update_marker(job_dir, use_relion_gui=not use_relion_gui)
    SelectClassesInteractiveContinue(job_dir).continue_job(
        use_relion_gui=use_relion_gui
    )
    assert marker.exists() is (not use_relion_gui)
    assert USE_RELION_GUI not in job_dir.get_job_params_as_dict()


def test_use_relion_gui_in_widgets(himena_ui: MainWindow, in_project: Path):
    job_dir = _make_project(in_project)
    update_marker(job_dir)
    himena_ui.read_file(job_dir.job_star())
    widget = _job_widget(himena_ui, job_dir)
    param_view = next(
        w for w in widget._iter_job_widgets() if isinstance(w, QJobParameterView)
    )
    toggle = param_view._param_widget._mgui_widgets[USE_RELION_GUI]
    assert toggle.value is False

    # overwrite/clone start from the current value
    for open_scheduler in [_impl.overwrite_relion_job, _impl.clone_relion_job]:
        scheduler = open_scheduler(himena_ui, job_dir)
        assert scheduler.get_parameters()[USE_RELION_GUI] is False

    # the job that was run by RELION
    update_marker(job_dir, use_relion_gui=True)
    param_view.on_job_updated(job_dir, job_dir.path / FileNames.USE_HIMENA_IMPL)
    assert toggle.value is True
    for open_scheduler in [_impl.overwrite_relion_job, _impl.clone_relion_job]:
        scheduler = open_scheduler(himena_ui, job_dir)
        assert scheduler.get_parameters()[USE_RELION_GUI] is True
