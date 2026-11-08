from typing import Callable
from pathlib import Path

import mrcfile
from qtpy import QtWidgets as QtW
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5_tomo.widgets._reconstruct import QReconstructViewer, _MAX_RETRY
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
    for i in range(5):
        QtW.QApplication.processEvents()

def test_reconstruct_particle_widget_intermediate(
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
    tester.mkdir("temp")
    tester.write_random_mrc("temp/sum_2_data_half1.mrc", (64, 32, 17))
    tester.write_random_mrc("temp/sum_2_ctf_half1.mrc", (32, 32, 17))
    tester.write_random_mrc("temp/sum_2_ctf_half0.mrc", (32, 32, 17))
    tester.write_random_mrc("temp/sum_2_data_half0.mrc", (64, 32, 17))
    assert tester.widget._viewer.has_image
    for i in range(5):
        QtW.QApplication.processEvents()

def test_reconstruct_particle_widget_retry(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    star_text = Path(jobs_dir_tomo / "Reconstruct" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Reconstruct")

    tester = JobWidgetTester(QReconstructViewer(job_dir), job_dir)
    widget = tester.widget
    qtbot.addWidget(widget)
    tester.mkdir("temp")
    fp = job_dir.path / "temp" / "sum_2_data_half0.mrc"
    with mrcfile.new(fp) as mrc:
        mrc.set_data(tester.make_random_mrc((64, 32, 17)))
    content = fp.read_bytes()

    # file is not completely written yet
    fp.write_bytes(content[: len(content) // 2])
    widget.on_job_updated(job_dir, str(fp))
    assert not widget._viewer.has_image
    assert widget._retry_timer.isActive()

    # retried after the file is written
    fp.write_bytes(content)
    qtbot.waitUntil(lambda: widget._viewer.has_image, timeout=3000)
    assert not widget._retry_timer.isActive()
    assert widget._num_retry == 0

    # retry stops if the file stays broken
    widget._retry_timer.setInterval(10)
    fp.write_bytes(content[: len(content) // 2])
    widget.on_job_updated(job_dir, str(fp))
    qtbot.waitUntil(
        lambda: widget._num_retry == _MAX_RETRY and not widget._retry_timer.isActive(),
        timeout=3000,
    )
