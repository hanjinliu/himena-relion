from typing import Callable
from pathlib import Path

import numpy as np
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5_tomo.widgets._aligntilt import QAlignTiltSeriesViewer
from himena_relion.testing import JobWidgetTester

def test_aligntilt_aretomo2(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    star_text = Path(jobs_dir_tomo / "AlignTiltSeries" / "job003" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "AlignTiltSeries")

    tester = JobWidgetTester(QAlignTiltSeriesViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)
    tester.mkdir("external")
    tester.mkdir("external/TS_01")
    tester.write_text("external/TS_01/TS_01.log", "LOG")
    tester.write_random_mrc("external/TS_01/TS_01_aligned.mrc", (40, 100, 100), dtype=np.float16)
    tester.mkdir("external/TS_02")

    assert tester.widget._viewer.has_image
    assert tester.widget._ts_list.rowCount() == 1
    assert tester.widget._align_log.toPlainText() == "LOG"
