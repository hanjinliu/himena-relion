from typing import Callable
from qtpy.QtWidgets import QApplication
from pathlib import Path
import numpy as np
from himena_relion._job_dir import JobDirectory
from himena_relion.testing import JobWidgetTester

def test_extract_spa(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    from himena_relion.relion5.widgets._extract import QExtractViewer
    star_text = Path(jobs_dir_spa / "Extract" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Extract")

    tester = JobWidgetTester(QExtractViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    tester.mkdir("Movies")
    assert tester.widget._mic_list.rowCount() == 0
    tester.write_random_mrc("Movies/i00.mrcs", (200, 32, 32), dtype=np.float16)
    tester.write_text("Movies/i00_extract.star", "")
    assert tester.widget._mic_list.rowCount() == 1
    tester.write_random_mrc("Movies/i01.mrcs", (122, 32, 32), dtype=np.float16)
    tester.write_text("Movies/i01_extract.star", "")
    assert tester.widget._mic_list.rowCount() == 2
    tester.write_random_mrc("Movies/i02.mrcs", (12, 30, 30), dtype=np.float16)
    tester.write_text("Movies/i02_extract.star", "")
    assert tester.widget._mic_list.rowCount() == 3

    tester.widget._slider.setValue(1)
    QApplication.processEvents()
    tester.widget._slider.setValue(0)
    QApplication.processEvents()
    tester.widget._mic_list.set_current_row(1)
    QApplication.processEvents()
    tester.widget._mic_list.set_current_row(2)
    QApplication.processEvents()

def test_extract_tomo_2d(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    from himena_relion.relion5_tomo.widgets._extract import QExtractJobViewer

    star_text = Path(jobs_dir_tomo / "Extract" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Extract")

    tester = JobWidgetTester(QExtractJobViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    tester.mkdir("Subtomograms")

    assert tester.widget._tomo_list.rowCount() == 0
    tester.mkdir("Subtomograms/TS_01")
    for i in range(6):
        tester.write_random_mrc(
            f"Subtomograms/TS_01/{i}_stack2d.mrcs",
            (5, 32, 32),
            dtype=np.float16
        )
    assert tester.widget._tomo_list.rowCount() == 1
    tester.mkdir("Subtomograms/TS_03")
    for i in range(3):
        tester.write_random_mrc(
            f"Subtomograms/TS_03/{i}_stack2d.mrcs",
            (5, 32, 32),
            dtype=np.float16
        )
    assert tester.widget._tomo_list.rowCount() == 2

def test_extract_tomo_3d(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    from himena_relion.relion5_tomo.widgets._extract import QExtractJobViewer

    star_text = Path(jobs_dir_tomo / "Extract" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Extract")

    tester = JobWidgetTester(QExtractJobViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    tester.mkdir("Subtomograms")

    assert tester.widget._tomo_list.rowCount() == 0
    tester.mkdir("Subtomograms/TS_01")
    for i in range(6):
        tester.write_random_mrc(
            f"Subtomograms/TS_01/{i}_data.mrc",
            (5, 32, 32),
            dtype=np.float16
        )
    assert tester.widget._tomo_list.rowCount() == 1
    tester.mkdir("Subtomograms/TS_03")
    for i in range(3):
        tester.write_random_mrc(
            f"Subtomograms/TS_03/{i}_data.mrc",
            (5, 32, 32),
            dtype=np.float16
        )
    assert tester.widget._tomo_list.rowCount() == 2


def test_extract_spa_batch_update(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
    monkeypatch,
):
    from himena_relion.relion5.widgets._extract import QExtractViewer

    star_text = Path(jobs_dir_spa / "Extract" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Extract")
    tester = JobWidgetTester(QExtractViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)
    tester.mkdir("Movies")
    tester.mkdir("Other")
    paths = []
    for subdir, i in [("Movies", 10), ("Movies", 2), ("Other", 1)]:
        path = job_dir.path / subdir / f"i{i:02d}.mrcs"
        tester.write_random_mrc(f"{subdir}/i{i:02d}.mrcs", (i, 16, 16))
        star_path = path.with_name(f"i{i:02d}_extract.star")
        star_path.write_text("")
        paths.extend([path, star_path])

    num_calls = 0
    _process_update = tester.widget._process_update

    def _spy():
        nonlocal num_calls
        num_calls += 1
        _process_update()

    monkeypatch.setattr(tester.widget, "_process_update", _spy)
    tester.widget.on_job_files_updated(job_dir, paths)
    assert num_calls == 1
    rel = job_dir.make_relative_path(job_dir.path).as_posix()
    assert tester.widget._mic_list._model._data == [
        ("i02.mrcs", "2", f"{rel}/Movies/i02.mrcs"),
        ("i10.mrcs", "10", f"{rel}/Movies/i10.mrcs"),
        ("i01.mrcs", "1", f"{rel}/Other/i01.mrcs"),
    ]
    # .mrcs files alone do not trigger the update
    tester.widget.on_job_files_updated(job_dir, [paths[0]])
    assert num_calls == 1


def test_extract_tomo_skips_replot(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
    monkeypatch,
):
    import mrcfile
    from himena_relion.relion5_tomo.widgets._extract import (
        QExtractJobViewer,
        _list_subtomo_names,
    )

    star_text = Path(jobs_dir_tomo / "Extract" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Extract")
    widget = QExtractJobViewer(job_dir)
    tester = JobWidgetTester(widget, job_dir)
    qtbot.addWidget(widget)
    tester.mkdir("Subtomograms/TS_01")
    num = widget._num_page + 1
    for i in range(1, num + 1):
        path = job_dir.path / f"Subtomograms/TS_01/{i}_stack2d.mrcs"
        with mrcfile.new(path) as mrc:
            mrc.set_data(tester.make_random_mrc((5, 16, 16), dtype=np.float16))
            mrc.voxel_size = (1.0, 1.0, 1.0)

    # natural sort, not the order of os.listdir
    names = _list_subtomo_names(job_dir, "TS_01")
    assert names[:3] == ["1_stack2d.mrcs", "2_stack2d.mrcs", "3_stack2d.mrcs"]
    assert names[-1] == f"{num}_stack2d.mrcs"

    widget.initialize(job_dir)
    widget.show()  # showEvent plots the first page
    qtbot.waitUntil(lambda: widget._plotted_page_complete, timeout=5000)
    assert widget._worker is None
    assert widget._plotted_page[1] == tuple(names[: widget._num_page])

    num_plots = 0
    _slider_value_changed = widget._slider_value_changed

    def _spy(*args, **kwargs):
        nonlocal num_plots
        num_plots += 1
        return _slider_value_changed(*args, **kwargs)

    monkeypatch.setattr(widget, "_slider_value_changed", _spy)

    # a new subtomogram out of the current page: not plotted again
    new_path = job_dir.path / f"Subtomograms/TS_01/{num + 1}_stack2d.mrcs"
    with mrcfile.new(new_path) as mrc:
        mrc.set_data(tester.make_random_mrc((5, 16, 16), dtype=np.float16))
    widget._last_force_reloaded = -1.0
    widget.on_job_files_updated(job_dir, [new_path] * 3)
    qtbot.waitUntil(lambda: widget._worker is None, timeout=5000)
    assert len(widget._subtomo_paths) == num + 1  # rescanned
    assert num_plots == 0
    assert widget._slider.maximum() == 1
    assert widget._slider_display_range.text() == f"1 - {widget._num_page}"

    # moving to the next page plots the subtomograms
    widget._slider.setValue(1)
    qtbot.waitUntil(lambda: widget._plotted_page_complete, timeout=5000)
    assert widget._plotted_page[1] == (names[-1], new_path.name)
    widget.hide()
