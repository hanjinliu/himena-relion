import time
from typing import Callable
from pathlib import Path

import threading
import mrcfile
import numpy as np
import polars as pl
from starfile_rs import as_star, read_star
from himena_relion._job_dir import ExternalJobDirectory, JobDirectory
from himena_relion.testing import ExternalJobTester
from himena_relion.schemas import (
    TSGroupModel,
    TSModel,
    RelionPipelineModel,
    TomogramsGroupModel,
    CoordsModel,
    MicrographsStarModel,
    ParticleMetaModel,
    ParticlesModel,
)

def test_shift_map(qtbot, tmpdir):
    from himena_relion.relion5.extensions import ShiftMapJob

    tmpdir = Path(tmpdir)
    ext_dir = tmpdir / "External/job010"
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_path = ext_dir / "in_3dref.mrc"
    mask_path = ext_dir / "in_mask.mrc"

    with mrcfile.new(img_path) as mrc:
        mrc.set_data(np.random.normal(size=(8, 8, 8)).astype(np.float32))
    with mrcfile.new(mask_path) as mrc:
        mrc.set_data(np.random.normal(size=(8, 8, 8)).astype(np.float32))
        mrc.voxel_size = (0.78, 0.78, 0.78)

    tester = ExternalJobTester(ShiftMapJob)
    job_ins = tester.create_job_instance(ext_dir)
    job_ins._log_job_version_info()
    widget = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)
    tester.prep_job_star(ext_dir, in_3dref=str(img_path), center_by="pixel", new_center=(1, 0, -1.2))
    tester.prep_job_star(ext_dir, in_3dref=str(img_path), center_by="angstrom", new_center=(1, 0, -1.2))
    tester.prep_job_star(ext_dir, in_3dref=str(img_path), center_by="map-com")
    tester.prep_job_star(ext_dir, in_3dref=str(img_path), in_mask=str(mask_path), center_by="map-com")

def test_shift_map_widget_retry(qtbot, tmpdir):
    from himena_relion.relion5.extensions import ShiftMapJob
    from himena_relion.relion5.extensions.transform import _const as _c

    tmpdir = Path(tmpdir)
    ext_dir = tmpdir / "External/job010"
    ext_dir.mkdir(parents=True, exist_ok=True)
    job_dir = ExternalJobDirectory(ext_dir)
    widget = ExternalJobTester(ShiftMapJob).provide_widget(ext_dir)
    qtbot.addWidget(widget)
    timer = widget._retry_timer
    fp = ext_dir / _c.OUTPUT_MAP
    with mrcfile.new(fp) as mrc:
        mrc.set_data(np.random.normal(size=(8, 8, 8)).astype(np.float32))
    content = fp.read_bytes()

    # file is not completely written yet
    fp.write_bytes(content[: len(content) // 2])
    widget.on_job_updated(job_dir, str(fp))
    assert not widget._viewer.has_image
    assert timer.isActive()

    # retried after the file is written
    fp.write_bytes(content)
    qtbot.waitUntil(lambda: widget._viewer.has_image, timeout=3000)
    assert not timer.isActive()
    assert timer.num_retry == 0

    # retry stops if the file stays broken
    timer.setInterval(10)
    fp.write_bytes(content[: len(content) // 2])
    widget.on_job_updated(job_dir, str(fp))
    qtbot.waitUntil(
        lambda: timer.num_retry == timer.max_retry and not timer.isActive(),
        timeout=3000,
    )

def test_shift_map_restores_optics(tmpdir):
    from himena_relion.relion5.extensions.transform.jobs import _restore_optics

    tmpdir = Path(tmpdir)
    df_optics = pl.DataFrame(
        {
            "rlnOpticsGroupName": ["opticsGroup1", "opticsGroup2"],
            "rlnOpticsGroup": [1, 2],
            "rlnImagePixelSize": [1.05, 0.78],
        }
    )
    df_parts = pl.DataFrame(
        {
            "rlnImageName": ["1@a.mrcs", "2@a.mrcs", "1@b.mrcs"],
            "rlnOpticsGroup": [1, 1, 2],
            "rlnOriginXAngst": [0.5, -1.25, 3.0],
        }
    )
    path_in = tmpdir / "in.star"
    as_star({"optics": df_optics, "particles": df_parts}).write(path_in)

    # relion_star_handler --ignore_optics writes the particles table only
    df_shifted = df_parts.with_columns(pl.col("rlnOriginXAngst") + 1.0)
    for block_name in ["particles", ""]:
        path_no_optics = tmpdir / "out_no_optics.star"
        path_out = tmpdir / "out.star"
        as_star({block_name: df_shifted}).write(path_no_optics)
        text_no_optics = path_no_optics.read_text()
        _restore_optics(path_in, path_no_optics, path_out)
        assert path_no_optics.read_text() == text_no_optics

        star_out = read_star(path_out)
        assert list(star_out.keys()) == ["optics", "particles"]
        assert star_out["optics"].trust_loop().to_polars().equals(df_optics)
        assert star_out["particles"].trust_loop().to_polars().equals(df_shifted)

    # input without the optics block is copied as is
    path_in_old = tmpdir / "in_old.star"
    as_star({"": df_parts}).write(path_in_old)
    path_no_optics = tmpdir / "out_old_no_optics.star"
    path_out = tmpdir / "out_old.star"
    as_star({"": df_shifted}).write(path_no_optics)
    _restore_optics(path_in_old, path_no_optics, path_out)
    assert path_out.read_text() == path_no_optics.read_text()


def test_inspect_particles_spa(qtbot, tmpdir):
    from himena_relion.relion5.extensions.inspect_particles import InspectParticlesSPA, InspectParticlesSPAWidget

    tmpdir = Path(tmpdir)
    mic_dir = tmpdir / "micrographs"
    mic_dir.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        with mrcfile.new(mic_dir / f"mic{i}.mrc") as mrc:
            mrc.set_data(np.random.normal(size=(8, 8)).astype(np.float32))
            mrc.voxel_size = (0.78, 0.78, 0.78)

    ext_dir = tmpdir / "External/job010"
    ext_dir.mkdir(parents=True, exist_ok=True)
    mic_path = ext_dir / "micrographs.star"
    parts_path = ext_dir / "particles.star"

    mic_path.write_text(
        MicrographsStarModel(
            optics=MicrographsStarModel.Optics(
                optics_group_name=["group1"],
                optics_group=[1],
                mic_orig_pixel_size=[0.78],
                voltage=[300],
                cs=[2.7],
            ),
            micrographs=MicrographsStarModel.Micrographs(
                mic_name=[f"micrographs/mic{i}.mrc" for i in range(3)],
                optics_group=[1, 1, 1],
            )
        ).to_string()
    )
    parts_path.write_text(
        CoordsModel(
            x=[4, 5, 4, 5, 6, 7, 8, 3, 4],
            y=[4, 4, 5, 5, 6, 7, 8, 3, 4],
            orig_x=[0.1] * 9,
            orig_y=[0.1] * 9,
            mic_name=[f"mic{i}.mrc" for i in [0, 0, 0, 1, 1, 1, 2, 2, 2]],
        ).to_string()
    )

    tester = ExternalJobTester(InspectParticlesSPA)
    widget = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)
    tester.prep_job_star(ext_dir, in_mics=str(mic_path), in_parts=str(parts_path))
    tester.test_run(ext_dir, widget=widget)
    assert isinstance(widget, InspectParticlesSPAWidget)
    widget._show_points_switch.value = False
    widget._show_points_switch.value = True

def _prep_ctffind_job(ctffind_dir: JobDirectory):
    ctffind_dir.path.joinpath("frames").mkdir()
    ctffind_dir.path.joinpath("tilt_series").mkdir()
    ctffind_dir_rel = ctffind_dir.make_relative_path(ctffind_dir.path)

    rng = np.random.default_rng(291)
    ts_group = TSGroupModel(
        tomo_name=[f"TS_0{i}" for i in range(3)],
        tomo_tilt_series_star_file=[str(ctffind_dir_rel / f"tilt_series/TS_0{i}.star") for i in range(3)],
        voltage=[200, 200, 200],
        cs=[2.7, 2.7, 2.7],
        amplitude_contrast=[0.1, 0.1, 0.1],
        original_pixel_size=[1.0, 1.0, 1.0],
        tomo_hand=[1, 1, 1],
    )

    for i in range(3):
        gs = TSModel(
            frame_count=[4, 4, 4, 4, 4],
            nominal_stage_tilt_angle=[-40, -20, 0, 20, 60],
            nominal_tilt_axis_angle=[85, 85, 85, 85, 85],
            pre_exposure=[0, 0, 0, 0, 0],
            nominal_defocus=[-2, -2, -2, -2, -2],
            micrograph_name=[
                str(ctffind_dir_rel / f"frames/TS_0{i}_{j}.mrc") for j in range(5)
            ],
        )
        for j in range(5):
            star_stem = f"TS_0{i}_{j}"
            path_mrc = ctffind_dir.path.joinpath(f"frames/{star_stem}.mrc")
            with mrcfile.new(path_mrc) as mrc:
                if j == 0:
                    img = -np.ones((8, 8), dtype=np.float32)
                else:
                    img = rng.normal(size=(8, 8)).astype(np.float32)
                mrc.set_data(img)
                mrc.voxel_size = (0.78, 0.78, 0.78)

        ctffind_dir.path.joinpath(f"tilt_series/TS_0{i}.star").write_text(gs.to_string())

    ctffind_dir.path.joinpath("tilt_series_ctf.star").write_text(ts_group.to_string())


def test_exclude_tilts_job(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    from himena_relion.relion5_tomo.extensions import AutoExcludeTiltImages

    star_text = Path(jobs_dir_tomo).joinpath("CtfFind/job001/job.star").read_text()
    ctffind_dir = make_job_directory(star_text, "CtfFind")
    _prep_ctffind_job(ctffind_dir)
    ctffind_dir_rel = ctffind_dir.make_relative_path(ctffind_dir.path)

    ext_dir = ctffind_dir.relion_project_dir.joinpath("External/job039")
    ext_dir.mkdir(parents=True, exist_ok=True)

    tester = ExternalJobTester(AutoExcludeTiltImages)
    tester.prep_job_star(ext_dir, in_mics=ctffind_dir_rel/"tilt_series_ctf.star")
    widget = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)

    # with the default threshold, about half of the pixels of random images are
    # "dark", so all the tilts are excluded
    tester.test_run(ext_dir, widget=widget)
    assert widget._excluded_list.rowCount() == 15
    assert [widget._ts_choice.text(i, 1) for i in range(3)] == ["0", "0", "0"]
    assert not widget._viewer.has_image

    # only the first tilt of each tilt series is dark
    tester.prep_job_star(
        ext_dir,
        in_mics=ctffind_dir_rel/"tilt_series_ctf.star",
        dark_pixel_percentage=90.0,
    )
    tester.test_run(ext_dir, widget=widget)
    assert [widget._excluded_list.text(i) for i in range(widget._excluded_list.rowCount())] == [
        str(ctffind_dir_rel / f"frames/TS_0{i}_0.mrc") for i in range(3)
    ]
    assert widget._excluded_viewer.has_image
    assert [widget._ts_choice.text(i, 1) for i in range(3)] == ["4", "4", "4"]
    assert widget._viewer.has_image
    widget._filter_widget.set_params(2, 0)
    widget._excluded_list.set_current_row(2)


def test_exclude_tilts_builtin_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    from himena_relion.testing import JobWidgetTester
    from himena_relion.relion5_tomo.widgets._tilt_series import QExcludeTiltViewer

    star_text = Path(jobs_dir_tomo).joinpath("CtfFind/job001/job.star").read_text()
    ctffind_dir = make_job_directory(star_text, "CtfFind")
    _prep_ctffind_job(ctffind_dir)
    ctffind_dir_rel = ctffind_dir.make_relative_path(ctffind_dir.path)
    in_star_rel = (ctffind_dir_rel / "tilt_series_ctf.star").as_posix()

    star_text = (
        Path(jobs_dir_tomo)
        .joinpath("ExcludeTiltImages/job001/job.star")
        .read_text()
        .replace("****", in_star_rel)
    )
    job_dir = make_job_directory(star_text, "ExcludeTiltImages")
    job_dir.path.joinpath("tilt_series").mkdir()
    job_dir_rel = job_dir.make_relative_path(job_dir.path)
    tester = JobWidgetTester(QExcludeTiltViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)
    content = tester.widget._content

    # nothing is listed before the selection is saved
    assert content._excluded_list.rowCount() == 0
    assert content._ts_choice.rowCount() == 0

    # TS_00 drops tilt 0, TS_01 drops tilts 0 and 4, TS_02 is dropped entirely
    kept_indices = {"TS_00": [1, 2, 3, 4], "TS_01": [1, 2, 3]}
    df_group = read_star(ctffind_dir.path / "tilt_series_ctf.star").first().trust_loop().to_polars()
    for tomo_name, indices in kept_indices.items():
        df_ts = read_star(ctffind_dir.path / f"tilt_series/{tomo_name}.star").first().trust_loop().to_polars()
        txt = as_star({tomo_name: df_ts[indices]}).to_string()
        tester.write_text(f"tilt_series/{tomo_name}.star", txt)
    df_selected = df_group.filter(pl.col("rlnTomoName").is_in(list(kept_indices))).with_columns(
        pl.col("rlnTomoName")
        .map_elements(lambda n: (job_dir_rel / f"tilt_series/{n}.star").as_posix(), return_dtype=pl.String)
        .alias("rlnTomoTiltSeriesStarFile")
    )
    tester.write_text("selected_tilt_series.star", as_star({"global": df_selected}).to_string())

    excluded = [content._excluded_list.text(i) for i in range(content._excluded_list.rowCount())]
    assert excluded == [
        str(ctffind_dir_rel / f"frames/{name}.mrc")
        for name in ["TS_00_0", "TS_01_0", "TS_01_4"] + [f"TS_02_{j}" for j in range(5)]
    ]
    assert content._excluded_viewer.has_image
    assert content._ts_choice.rowCount() == 2
    assert [content._ts_choice.text(i, 1) for i in range(2)] == ["4", "3"]
    assert content._viewer.has_image
    assert content._viewer._dims_slider.maximum() == 3
    content._filter_widget.set_params(2, 0)
    content._excluded_list.set_current_row(3)
    content._ts_choice.set_current_row(1)
    assert content._viewer._dims_slider.maximum() == 2

def _findbeads3d_wrapped(
    exe: str,
    tomo_path: str | Path,
    out_path: str | Path,
    size_pix: float,
    angle_range: tuple[float, float] = (-60.0, 60.0),
):
    import imodmodel
    import pandas as pd

    df = pd.DataFrame({"x": [0, 10], "y": [0, 40], "z": [0, 10]})
    imodmodel.write(df, out_path)

def test_erase_gold(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
    monkeypatch,
):
    from himena_relion.relion5_tomo.extensions.erase_gold import (
        FindBeads3D, EraseGold, _impl
    )

    monkeypatch.setattr(_impl, "findbeads3d_wrapped", _findbeads3d_wrapped)

    star_text = Path(jobs_dir_tomo).joinpath("CtfFind/job001/job.star").read_text()
    ctffind_dir = make_job_directory(star_text, "CtfFind")
    _prep_ctffind_job(ctffind_dir)
    ctffind_dir_rel = ctffind_dir.make_relative_path(ctffind_dir.path)
    with mrcfile.new(ctffind_dir.path.joinpath("tomo.mrc")) as mrc:
        mrc.set_data(np.ones((8, 8, 8), dtype=np.float32))
    df = read_star(
        ctffind_dir.path.joinpath("tilt_series_ctf.star")
    ).first().to_polars()
    df = df.with_columns(
        pl.lit(str(ctffind_dir_rel/"tomo.mrc")).alias("rlnTomoReconstructedTomogram"),
        pl.lit(str(ctffind_dir_rel/"tomo.edf")).alias("rlnEtomoDirectiveFile"),
    )
    np.savetxt(
        ctffind_dir.path / "tomo.xf",
        np.array([[0.01, 0.99, -0.99, 0.01, -1, 2]] * 5),
        delimiter=" ",
    )

    as_star({"global": df}).write(ctffind_dir.path.joinpath("tilt_series_ctf.star"))

    findbeads_dir = ctffind_dir.relion_project_dir.joinpath("External/job039")
    findbeads_dir.mkdir(parents=True, exist_ok=True)
    tester = ExternalJobTester(FindBeads3D)
    tester.prep_job_star(
        findbeads_dir,
        findbeads3d_exe="***",
        in_mics=ctffind_dir_rel/"tilt_series_ctf.star"
    )
    findbeads_dir.joinpath("job_pipeline.star").write_text(
        RelionPipelineModel(
            general=RelionPipelineModel.General(count=5),
            processes=RelionPipelineModel.Processes(
                process_name=["External/job039/"],
                alias=["alias"],
                type_label=["type"],
                status_label=["Succeeded"],
            ),
            nodes=RelionPipelineModel.Nodes(
                name=[str(ctffind_dir_rel/"tilt_series_ctf.star")],
                type_label=["TomogramGroupMetadata.star"],
                type_label_depth=[1],
            ),
            input_edges=RelionPipelineModel.InputEdges(
                from_node=[str(ctffind_dir_rel/"tilt_series_ctf.star")],
                process=["External/job039/"],
            )
        ).to_string()
    )
    widget = tester.provide_widget(findbeads_dir)
    qtbot.addWidget(widget)
    tester.test_run(findbeads_dir, widget=widget)

    erasegold_dir = ctffind_dir.relion_project_dir.joinpath("External/job040")
    erasegold_dir.mkdir(parents=True, exist_ok=True)
    tester = ExternalJobTester(EraseGold)
    tester.prep_job_star(erasegold_dir, in_mics="External/job039/tomograms.star")
    widget = tester.provide_widget(erasegold_dir)
    qtbot.addWidget(widget)
    tester.test_run(erasegold_dir, widget=widget)

def test_take_zerotilts(
    qtbot,
    tmpdir,
    jobs_dir_tomo,
):
    from himena_relion.relion5_tomo.extensions import TakeZeroTiltMicrographs

    rln_dir = Path(tmpdir)
    frames_dir = rln_dir.joinpath("frames")
    frames_dir.mkdir(parents=True, exist_ok=True)
    for i in range(4):
        for j in range(5):
            with mrcfile.new(frames_dir.joinpath(f"TS_0{i}_{j}.mrc")) as mrc:
                mrc.set_data(np.random.normal(size=(8, 8)).astype(np.float32))
                mrc.voxel_size = (0.78, 0.78, 0.78)

    some_dir = rln_dir.joinpath("some_dir")
    tilt_series_dir = some_dir.joinpath("tilt_series")
    some_dir.mkdir(parents=True, exist_ok=True)
    tilt_series_dir.mkdir()

    # frames/
    #   TS_00_00.mrc
    #   TS_00_01.mrc
    #   ...
    # some_dir/
    #   tilt_series/
    #     TS_00.star
    #     TS_01.star
    #     ...
    #   tomograms.star
    #   run_data.star

    for i in range(4):
        ts_star = TSModel(
            movie_name=[f"TS_0{i}_{j}.mrc" for j in range(5)],
            frame_count=[4] * 5,
            nominal_stage_tilt_angle=[-40, -20, 0, 20, 60],
            nominal_tilt_axis_angle=[85] * 5,
            pre_exposure=[0] * 5,
            nominal_defocus=[-2] * 5,
            micrograph_name=[f"frames/TS_0{i}_{j}.mrc" for j in range(5)],
            tomo_xtilt=[1, 1, 2, 1, 2],
            tomo_ytilt=[1, 1, 2, 1, 2],
            tomo_zrot=[0, 0, 0, 0, 0],
            tomo_xshift_angst=[0.2, 0.2, 0.3, 0.2, 0.3],
            tomo_yshift_angst=[0.2, 0.2, 0.3, 0.2, 0.3],
        )
        tilt_series_dir.joinpath(f"TS_0{i}.star").write_text(ts_star.to_string())

    tomogram_star = TomogramsGroupModel(
        tomo_name=[f"TS_0{i}" for i in range(4)],
        voltage=[300] * 4,
        cs=[2.7] * 4,
        amplitude_contrast=[0.1] * 4,
        original_pixel_size=[0.78] * 4,
        tomo_hand=[1] * 4,
        optics_group_name=["group1", "group1", "group2", "group2"],
        tomo_tilt_series_pixel_size=[0.78, 0.78, 0.78, 0.78],
        tomo_tilt_series_star_file=[f"some_dir/tilt_series/TS_0{i}.star" for i in range(4)],
        tomogram_binning=[1.0] * 4,
        size_x=[4000] * 4,
        size_y=[3000] * 4,
        size_z=[1000] * 4,
    )
    some_dir.joinpath("tomograms.star").write_text(tomogram_star.to_string())

    run_data = ParticleMetaModel(
        particles=ParticlesModel(
            tomo_name=[f"TS_0{i}" for i in range(4) for _ in range(10)],
            centered_x=[0.0] * 40,
            centered_y=[0.0] * 40,
            centered_z=[0.0] * 40,
            orig_x=[0.0] * 40,
            orig_y=[0.0] * 40,
            orig_z=[0.0] * 40,
            angle_rot=[0.0] * 40,
            angle_tilt=[0.0] * 40,
        )
    )
    some_dir.joinpath("particles.star").write_text(run_data.to_string())

    ext_dir = rln_dir.joinpath("External/job001")
    ext_dir.mkdir(parents=True, exist_ok=True)
    tester = ExternalJobTester(TakeZeroTiltMicrographs)
    tester.prep_job_star(ext_dir, in_mics="some_dir/tomograms.star", in_parts="some_dir/particles.star")
    widget = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)
    tester.test_run(ext_dir, widget=widget)

def test_manually_create_mask(
    qtbot,
    tmpdir,
    jobs_dir_spa,
):
    from himena_relion.relion5.extensions.volume_tools import ManualMaskCreation
    from himena_relion.relion5.extensions.volume_tools.widgets import QMaskCreateViewer

    tmpdir = Path(tmpdir)
    template_path = tmpdir / "in_3dref.mrc"
    with mrcfile.new(template_path) as mrc:
        mrc.set_data(np.random.normal(size=(8, 8, 8)).astype(np.float32))
        mrc.voxel_size = (0.78, 0.78, 0.78)
    ext_dir = tmpdir / "External/job010"
    ext_dir.mkdir(parents=True, exist_ok=True)

    tester = ExternalJobTester(ManualMaskCreation)
    ManualMaskCreation._max_wait_time_sec = 5
    tester.prep_job_star(ext_dir, in_3dref=str(template_path))
    widget: QMaskCreateViewer = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)

    mask_path = ext_dir / "mask_base.mrc"
    def create_mask():
        time.sleep(0.5)
        with mrcfile.new(mask_path, overwrite=True) as mrc:
            mrc.set_data(np.random.normal(size=(8, 8, 8)).astype(np.float32))
            mrc.voxel_size = (0.78, 0.78, 0.78)

    thread = threading.Thread(target=create_mask, daemon=True)
    thread.start()

    tester.test_run(ext_dir, widget=widget)

    widget._mask_level_slider.value = 0.4
    widget._step_size.setValue(2)
    widget._mask_mode.value = "wireframe"
    widget._mask_level_slider.value = 0.44
    assert (ext_dir / "mask.mrc").exists()
    assert (ext_dir / "mask_base.mrc").exists()

    # overwrite
    thread = threading.Thread(target=create_mask, daemon=True)
    thread.start()

    tester.test_run(ext_dir, widget=widget)
    assert (ext_dir / "mask.mrc").exists()
    assert (ext_dir / "mask_base.mrc").exists()


def _save_mrc_later(path: Path, data: np.ndarray) -> threading.Thread:
    """Save an MRC file after a while, as the user does in an external app."""

    def _save():
        time.sleep(0.5)
        with mrcfile.new(path, overwrite=True) as mrc:
            mrc.set_data(data)
            mrc.voxel_size = (0.78, 0.78, 0.78)

    thread = threading.Thread(target=_save, daemon=True)
    thread.start()
    return thread


def _read_mrc(path: Path) -> np.ndarray:
    with mrcfile.open(path) as mrc:
        return np.asarray(mrc.data)


def test_continue_drawing_mask(qtbot, himena_ui, tmp_path: Path, monkeypatch):
    import pytest
    from himena_relion import _job_class
    from himena_relion.consts import FileNames
    from himena_relion.relion5.extensions.volume_tools import jobs as _jobs
    from himena_relion.relion5.extensions.volume_tools import (
        ManualMaskCreation,
        ManualMaskCreationContinue,
    )
    from himena_relion.relion5.extensions.volume_tools.widgets import QMaskCreateViewer
    from himena_relion.schemas import JobStarModel

    monkeypatch.setattr(ManualMaskCreation, "_max_wait_time_sec", 5)
    launched: list[list[str]] = []
    monkeypatch.setattr(_jobs, "popen_detached", lambda args, **_: launched.append(args))
    monkeypatch.setattr(_jobs, "_find_chimera_exec", lambda: "chimerax")
    monkeypatch.setattr(_jobs, "relion_python_executable", lambda: "python")

    template_path = tmp_path / "in_3dref.mrc"
    with mrcfile.new(template_path) as mrc:
        mrc.set_data(np.random.normal(size=(8, 8, 8)).astype(np.float32))
        mrc.voxel_size = (0.78, 0.78, 0.78)
    ext_dir = tmp_path / "External/job010"
    ext_dir.mkdir(parents=True)
    mask_path = ext_dir / "mask.mrc"
    mask_base_path = ext_dir / "mask_base.mrc"
    tester = ExternalJobTester(ManualMaskCreation)
    tester.prep_job_star(ext_dir, in_3dref=str(template_path), use_app="Napari")
    widget: QMaskCreateViewer = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)

    # a new job starts from no mask
    small = np.zeros((8, 8, 8), dtype=np.uint8)
    small[3:5, 3:5, 3:5] = 1
    _save_mrc_later(mask_base_path, small)
    tester.test_run(ext_dir, widget=widget)
    assert launched[-1][2:] == [
        template_path.as_posix(),
        ext_dir.as_posix(),
        "--threshold",
        "0.5",
    ]
    mask_small = _read_mrc(mask_path)

    # continue editing in napari, starting from mask_base.mrc
    tester = ExternalJobTester(ManualMaskCreationContinue)
    large = np.zeros((8, 8, 8), dtype=np.uint8)
    large[1:7, 1:7, 1:7] = 1
    _save_mrc_later(mask_base_path, large)
    tester.test_continue(ext_dir, widget=widget, threshold=0.3, other_binning=[2.0])
    args = launched[-1]
    assert args[args.index("--mask") + 1] == mask_base_path.as_posix()
    assert args[args.index("--threshold") + 1] == "0.3"
    assert JobStarModel.validate_file(ext_dir / "job.star").job.job_is_continue == 1
    job_dir = ExternalJobDirectory(ext_dir)
    params = job_dir.get_job_params_as_dict()
    assert params["fn_exe"] == (
        "himena-relion himena_relion.relion5:ManualMaskCreationContinue"
    )
    assert params["in_3dref"] == str(template_path)
    assert (params["threshold"], params["use_app"]) == ("0.3", "Napari")
    assert job_dir._to_job_class() is ManualMaskCreation
    assert _read_mrc(mask_path).sum() > mask_small.sum()
    assert _read_mrc(ext_dir / "mask_bin2.0.mrc").shape == (4, 4, 4)

    # continue in ChimeraX, with a filtered map (created twice)
    for _ in range(2):
        _save_mrc_later(mask_base_path, small)
        tester.test_continue(ext_dir, use_app="Chimera/ChimeraX", pre_lowpass=10.0)
        filtered_path = ext_dir / "map_filtered.mrc"
        assert launched[-1] == [
            "chimerax",
            filtered_path.as_posix(),
            mask_base_path.as_posix(),
        ]
    np.testing.assert_allclose(_read_mrc(mask_path), mask_small)

    # mask.mrc given by the user is used as is
    user_mask = np.full((8, 8, 8), 0.25, dtype=np.float32)
    _save_mrc_later(mask_path, user_mask)
    tester.test_continue(ext_dir, use_app="None")
    np.testing.assert_allclose(_read_mrc(mask_path), user_mask)
    np.testing.assert_allclose(_read_mrc(ext_dir / "mask_bin2.0.mrc"), 0.25, atol=1e-5)

    # the continued job waits for the mask to be saved again
    monkeypatch.setattr(ManualMaskCreation, "_max_wait_time_sec", 0)
    with pytest.raises(TimeoutError):
        tester.test_continue(ext_dir)

    # continue from the widget
    assert "Editing the mask" in widget._message.text()
    ext_dir.joinpath(FileNames.EXIT_SUCCESS).touch()
    widget.on_job_updated(job_dir, str(ext_dir / FileNames.EXIT_SUCCESS))
    assert widget._message.text() == "mask.mrc"
    widget._continue_btn.click()
    scheduler = _job_class.scheduler_widget(himena_ui)
    assert scheduler._exec_btn.text() == "Continue Job"
    widgets = scheduler._job_param_widget._mgui_widgets
    assert not widgets["in_3dref"].enabled  # the input cannot be changed
    assert widgets["in_3dref"].value == str(template_path)
    assert scheduler.get_parameters()["threshold"] == pytest.approx(0.3)


def test_napari_mask_script(tmp_path: Path, monkeypatch):
    """Functions of the napari script, which is run in another process."""
    import importlib.util
    import sys
    import types
    from himena_relion.relion5.extensions import volume_tools

    # napari is not needed to test the functions
    monkeypatch.setitem(sys.modules, "napari", types.ModuleType("napari"))
    scripts_dir = Path(volume_tools.__file__).parent.parent / "scripts"
    spec = importlib.util.spec_from_file_location(
        "_mask_creation_napari", scripts_dir / "mask_creation_napari.py"
    )
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)

    args = script.parse_args(["map.mrc", "External/job001"])
    assert (args.mask, args.threshold) == (None, 0.5)
    args = script.parse_args(
        ["map.mrc", "External/job001", "--mask", "m.mrc", "--threshold", "0.3"]
    )
    assert (args.mask, args.threshold) == ("m.mrc", 0.3)

    data = np.zeros((4, 4, 4), dtype=np.float32)
    assert not script.initial_labels(data, None, 0.5).any()
    mask = np.full((4, 4, 4), 0.2, dtype=np.float32)
    mask[1:3] = 0.8
    with mrcfile.new(tmp_path / "mask.mrc") as mrc:
        mrc.set_data(mask)
    labels = script.initial_labels(data, str(tmp_path / "mask.mrc"), 0.5)
    assert labels.dtype == np.uint8
    np.testing.assert_array_equal(labels, mask > 0.5)
    assert script.initial_labels(data, str(tmp_path / "mask.mrc"), 0.1).all()
    # shape mismatch
    labels = script.initial_labels(np.zeros((2, 2, 2)), str(tmp_path / "mask.mrc"), 0.5)
    assert labels.shape == (2, 2, 2) and not labels.any()


_TOMOGRAMS_STAR = """
# version 50001

data_global

loop_
_rlnTomoName #1
_rlnTomoTiltSeriesPixelSize #2
_rlnTomoTiltSeriesStarFile #3
_rlnEtomoDirectiveFile #4
_rlnTomoReconstructedTomogram #5
TS_01	2.000000	Tomograms/job010/tilt_series/TS_01.star	""	Tomograms/job010/tomograms/rec_TS_01.mrc
TS_02	2.000000	Tomograms/job010/tilt_series/TS_02.star	""	Tomograms/job010/tomograms/rec_TS_02.mrc
001	2.000000	Tomograms/job010/tilt_series/001.star	""	Tomograms/job010/tomograms/rec_001.mrc
"""
_IN_TOMOGRAMS = "Tomograms/job010/tomograms.star"


def _prep_tomograms(project_dir: Path) -> Path:
    """Prepare the tomograms.star of a Reconstruct tomograms job and the tomograms."""
    tomo_dir = project_dir / "Tomograms/job010/tomograms"
    tomo_dir.mkdir(parents=True)
    for name in ["TS_01", "TS_02", "001"]:
        with mrcfile.new(tomo_dir / f"rec_{name}.mrc") as mrc:
            mrc.set_data(np.random.normal(size=(4, 16, 16)).astype(np.float32))
            mrc.voxel_size = (2.0, 2.0, 2.0)
    star_path = project_dir / _IN_TOMOGRAMS
    star_path.write_text(_TOMOGRAMS_STAR, newline="\n")
    ext_dir = project_dir / "External/job020"
    ext_dir.mkdir(parents=True)
    return ext_dir


def _selected_tomo_names(path: Path) -> list[str]:
    df = read_star(path).first().trust_loop().to_polars(string_columns=["rlnTomoName"])
    return df["rlnTomoName"].to_list()


def _save_selection_later(ext_dir: Path, selection: dict[str, bool]) -> threading.Thread:
    """Save the selection after a while, as the user does in the job widget."""
    from himena_relion.relion5_tomo.extensions.select_tomograms._impl import (
        save_selection,
    )

    def _save():
        time.sleep(0.5)
        save_selection(ExternalJobDirectory(ext_dir), selection)

    thread = threading.Thread(target=_save, daemon=True)
    thread.start()
    return thread


def test_select_tomograms(qtbot, himena_ui, tmp_path: Path, monkeypatch):
    import pytest
    from qtpy import QtCore
    from himena_relion import _job_class
    from himena_relion.consts import FileNames
    from himena_relion.relion5_tomo import SelectTomograms, SelectTomogramsContinue
    from himena_relion.relion5_tomo.extensions.select_tomograms._impl import (
        OUTPUT_STAR,
        SELECTION_STAR,
    )
    from himena_relion.relion5_tomo.extensions.select_tomograms.widgets import (
        QSelectTomogramsViewer,
    )
    from himena_relion.schemas import JobStarModel

    check_role = QtCore.Qt.ItemDataRole.CheckStateRole
    checked = QtCore.Qt.CheckState.Checked
    monkeypatch.setattr(SelectTomograms, "_poll_interval_sec", 0.01)
    monkeypatch.setattr(SelectTomograms, "_max_wait_time_sec", 5)
    ext_dir = _prep_tomograms(tmp_path)
    job_dir = ExternalJobDirectory(ext_dir)
    tester = ExternalJobTester(SelectTomograms)
    tester.prep_job_star(ext_dir, in_mics=_IN_TOMOGRAMS)
    widget: QSelectTomogramsViewer = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)
    widget.initialize(job_dir)

    # the job is running, and no tomograms are selected yet
    tomo_list = widget._tomo_list
    assert tomo_list.rowCount() == 3
    assert tomo_list.text(2) == "001"
    assert tomo_list.text(0, 1) == "full tomogram"
    assert tomo_list.checked() == [False, False, False]
    assert widget._viewer.has_image
    assert not widget._save_btn.isEnabled()
    assert widget._continue_btn.isHidden()
    assert "Save selection" in widget._message.text()

    # check by the space key, the check box and the buttons
    qtbot.keyClick(tomo_list, QtCore.Qt.Key.Key_Space)
    assert tomo_list.checked() == [True, False, False]
    qtbot.keyClick(tomo_list, QtCore.Qt.Key.Key_Space)
    assert tomo_list.checked() == [False, False, False]
    model = tomo_list.model()
    assert model.flags(model.index(0, 0)) & QtCore.Qt.ItemFlag.ItemIsUserCheckable
    assert model.setData(model.index(1, 0), checked.value, check_role)
    assert tomo_list.checked() == [False, True, False]
    assert widget._count_label.text() == "1 / 3 selected"
    assert widget._save_btn.isEnabled()
    widget._select_all_btn.click()
    assert tomo_list.checked() == [True, True, True]
    widget._deselect_all_btn.click()
    assert tomo_list.checked() == [False, False, False]
    assert not widget._save_btn.isEnabled()
    tomo_list.set_current_row(1)
    assert widget._filter_widget._spacer.text() == "(4, 16, 16) 2.00 Å/pix"

    # the job waits for the selection to be saved in the widget
    job = tester.create_job_instance(ext_dir)
    run = job.run(in_mics=_IN_TOMOGRAMS)
    next(run)
    next(run)
    assert not (ext_dir / OUTPUT_STAR).exists()
    model.setData(model.index(0, 0), checked, check_role)
    model.setData(model.index(2, 0), checked, check_role)
    widget._save_btn.click()
    assert (ext_dir / SELECTION_STAR).exists()
    assert "Selection saved" in widget._message.text()
    with pytest.raises(StopIteration):
        next(run)
    assert _selected_tomo_names(ext_dir / OUTPUT_STAR) == ["TS_01", "001"]
    # values are written as they are
    out_text = (ext_dir / OUTPUT_STAR).read_text()
    assert "TS_02" not in out_text
    assert '001\t2.000000\tTomograms/job010/tilt_series/001.star\t""\t' in out_text

    # the job finished
    ext_dir.joinpath(FileNames.EXIT_SUCCESS).touch()
    widget.on_job_updated(job_dir, str(ext_dir / FileNames.EXIT_SUCCESS))
    assert widget._message.text() == f"2 tomograms saved in {OUTPUT_STAR}."
    assert not widget._continue_btn.isHidden()
    assert widget._save_btn.isHidden()
    qtbot.keyClick(tomo_list, QtCore.Qt.Key.Key_Space)  # not checkable any more
    assert tomo_list.checked() == [True, False, True]
    assert not model.flags(model.index(0, 0)) & QtCore.Qt.ItemFlag.ItemIsUserCheckable
    assert not model.setData(model.index(1, 0), checked, check_role)

    # a new widget shows the saved selection
    widget_new: QSelectTomogramsViewer = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget_new)
    widget_new.initialize(job_dir)
    assert widget_new._tomo_list.checked() == [True, False, True]

    # continue from the widget
    widget._continue_btn.click()
    scheduler = _job_class.scheduler_widget(himena_ui)
    assert scheduler._exec_btn.text() == "Continue Job"
    widgets = scheduler._job_param_widget._mgui_widgets
    assert not widgets["in_mics"].enabled  # the input cannot be changed
    assert widgets["in_mics"].value == _IN_TOMOGRAMS

    # continued job starts from the last selection
    ext_dir.joinpath(FileNames.EXIT_SUCCESS).unlink()
    widget.on_job_updated(job_dir, str(ext_dir / FileNames.EXIT_SUCCESS))
    assert tomo_list.checked() == [True, False, True]
    assert tomo_list.is_checkable()
    assert widget._continue_btn.isHidden()
    tester = ExternalJobTester(SelectTomogramsContinue)
    _save_selection_later(ext_dir, {"TS_01": False, "TS_02": True, "001": False})
    tester.test_continue(ext_dir, widget=widget)
    assert _selected_tomo_names(ext_dir / OUTPUT_STAR) == ["TS_02"]
    assert JobStarModel.validate_file(ext_dir / "job.star").job.job_is_continue == 1
    assert job_dir.get_job_param("fn_exe") == (
        "himena-relion himena_relion.relion5_tomo:SelectTomogramsContinue"
    )
    assert job_dir._to_job_class() is SelectTomograms

    # tomograms not in the input are ignored, and some must be selected
    _save_selection_later(ext_dir, {"TS_01": True, "TS_99": True})
    tester.test_continue(ext_dir)
    assert _selected_tomo_names(ext_dir / OUTPUT_STAR) == ["TS_01"]
    _save_selection_later(ext_dir, {"TS_01": False, "TS_02": False, "001": False})
    with pytest.raises(ValueError, match="No tomograms selected"):
        tester.test_continue(ext_dir)

    # the job waits for the selection to be saved again
    monkeypatch.setattr(SelectTomograms, "_max_wait_time_sec", 0)
    with pytest.raises(TimeoutError):
        tester.test_continue(ext_dir)


def test_select_tomograms_inputs(qtbot, tmp_path: Path):
    import pytest
    from himena_relion.relion5_tomo import SelectTomograms
    from himena_relion.relion5_tomo.extensions.select_tomograms._impl import (
        TomogramSet,
    )
    from himena_relion.relion5_tomo.extensions.select_tomograms.widgets import (
        QSelectTomogramsViewer,
    )

    ext_dir = _prep_tomograms(tmp_path)
    df = pl.DataFrame(
        {
            "rlnTomoName": ["TS_01", "TS_02"],
            "rlnTomoReconstructedTomogramHalf1": [
                "Tomograms/job010/tomograms/rec_TS_01.mrc",
                "Tomograms/job010/tomograms/rec_TS_02.mrc",
            ],
            "rlnTomoReconstructedTomogramHalf2": [
                "Tomograms/job010/tomograms/rec_TS_01.mrc",
                "Tomograms/job010/tomograms/missing.mrc",
            ],
        }
    )
    halves_path = tmp_path / "halves.star"
    as_star({"global": df}).write(halves_path)
    entries = TomogramSet.from_file(halves_path).entries()
    assert [e.kind for e in entries] == ["half tomograms"] * 2
    assert len(entries[1].paths) == 2

    denoised_path = tmp_path / "denoised.star"
    df_denoised = df.with_columns(
        pl.Series("rlnTomoReconstructedTomogramDenoised", ["a.mrc", "b.mrc"])
    )
    as_star({"global": df_denoised}).write(denoised_path)
    entries = TomogramSet.from_file(denoised_path).entries()
    assert [e.kind for e in entries] == ["denoised tomogram"] * 2

    no_tomo_path = tmp_path / "no_tomo.star"
    as_star({"global": df.select("rlnTomoName")}).write(no_tomo_path)
    entries = TomogramSet.from_file(no_tomo_path).entries()
    assert [e.kind for e in entries] == ["not reconstructed"] * 2

    no_name_path = tmp_path / "no_name.star"
    as_star({"global": df.drop("rlnTomoName")}).write(no_name_path)
    with pytest.raises(ValueError, match="rlnTomoName"):
        TomogramSet.from_file(no_name_path)

    # the widget shows each kind of input
    tester = ExternalJobTester(SelectTomograms)
    job_dir = ExternalJobDirectory(ext_dir)
    tester.prep_job_star(ext_dir, in_mics=str(halves_path))
    widget: QSelectTomogramsViewer = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)
    widget.initialize(job_dir)
    assert widget._viewer.has_image
    widget._tomo_list.set_current_row(1)  # one of the halves is missing
    assert widget._viewer.has_image

    tester.prep_job_star(ext_dir, in_mics=str(denoised_path))
    widget.initialize(job_dir)  # tomogram names are the same
    widget._tomo_list.set_current_row(0)
    assert not widget._viewer.has_image
    assert widget._filter_widget._spacer.text() == "Tomogram file not found."

    tester.prep_job_star(ext_dir, in_mics=str(no_tomo_path))
    widget.initialize(job_dir)
    widget._tomo_list.set_current_row(1)
    assert widget._filter_widget._spacer.text() == "Tomogram is not reconstructed."

    tester.prep_job_star(ext_dir, in_mics=str(no_name_path))
    widget.initialize(job_dir)
    assert widget._tomo_list.rowCount() == 0
    assert "Failed to read" in widget._message.text()
    with pytest.raises(ValueError, match="rlnTomoName"):
        tester.test_run(ext_dir)
