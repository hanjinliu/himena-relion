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
