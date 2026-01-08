from typing import Callable
from qtpy.QtWidgets import QApplication
from pathlib import Path
import numpy as np
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._extract import QExtractViewer
from himena_relion.testing import JobWidgetTester

def test_extract_spa(
    qtbot,
    make_job_directory: Callable[[str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "Extract" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text)

    tester = JobWidgetTester(QExtractViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    job_dir.path.joinpath("Movies").mkdir()
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
    tester.widget._mic_list.setCurrentCell(1, 0)
    QApplication.processEvents()
    tester.widget._mic_list.setCurrentCell(2, 0)
    QApplication.processEvents()
