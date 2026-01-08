from typing import Callable
from qtpy.QtWidgets import QApplication
from pathlib import Path
import numpy as np
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._class2d import QClass2DViewer
from himena_relion.testing import JobWidgetTester
from himena_relion.schemas import ModelStarModel

def test_class2d(
    qtbot,
    make_job_directory: Callable[[str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "Class2D" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text)

    tester = JobWidgetTester(QClass2DViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    tester.write_text("run_it000_model.star", ModelStarModel.example(20).to_string())
    tester.write_random_mrc("run_it000_classes.mrcs", (20, 32, 32), dtype=np.float32)
    assert tester.widget._iter_choice.maximum() == 0
    tester.write_text("run_it010_model.star", ModelStarModel.example(20).to_string())
    tester.write_random_mrc("run_it010_classes.mrcs", (20, 32, 32), dtype=np.float32)
    assert tester.widget._iter_choice.maximum() == 10

    for _ in range(10):
        QApplication.processEvents()
