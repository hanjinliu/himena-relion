from typing import Callable
from qtpy.QtWidgets import QApplication
from pathlib import Path
import numpy as np
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._frames import QMotionCorrViewer
from himena_relion.testing import JobWidgetTester

def test_motioncor_widget(
    qtbot,
    make_job_directory: Callable[[str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "MotionCorr" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text)

    tester = JobWidgetTester(QMotionCorrViewer(job_dir), job_dir)

    qtbot.addWidget(tester.widget)
    assert tester.widget._mic_list.rowCount() == 0

    job_dir.path.joinpath("Movies").mkdir()
    for i in range(3):
        basename = f"Frame_{i:02d}"
        tester.write_random_mrc(f"Movies/{basename}.mrc", (10, 10), dtype=np.float16)
        tester.write_text(f"Movies/{basename}.log", "log ...")
        tester.write_text(f"Movies/{basename}.star", "star ...")
        tester.write_random_mrc(f"Movies/{basename}_PS.mrc", (10, 3), dtype=np.float16)

        assert tester.widget._mic_list.rowCount() == i + 1

    for _ in range(3):
        QApplication.processEvents()
