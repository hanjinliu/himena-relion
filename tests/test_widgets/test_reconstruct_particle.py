from typing import Callable
from qtpy.QtWidgets import QApplication
from pathlib import Path
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5_tomo.widgets._reconstruct import QReconstructViewer
from himena_relion.testing import JobWidgetTester

def test_reconstruct_particle_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    star_text = Path(jobs_dir_tomo / "Reconstruct" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Reconstruct")

    tester = JobWidgetTester(QReconstructViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)
    assert not tester.widget._viewer.has_image
    tester.widget.show()

    assert not tester.widget._viewer.has_image
    tester.write_random_mrc("merged.mrc", (32, 32, 32))
    assert tester.widget._viewer.has_image

    for _ in range(10):
        QApplication.processEvents()
