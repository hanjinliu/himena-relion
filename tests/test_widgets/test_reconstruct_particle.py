from typing import Callable
from pathlib import Path

import mrcfile
from qtpy import QtWidgets as QtW, QtCore
from himena_relion._job_dir import JobDirectory
from himena_relion import _impl_objects
from himena_relion.relion5_tomo.widgets._reconstruct import (
    QReconstructViewer,
    _MAX_RETRY,
    _ReadResult,
)
from himena_relion.testing import JobWidgetTester

def _delete_widgets_of_previous_tests():
    """Delete the widgets that previous tests scheduled for deletion.

    `processEvents` does not delete them, so more than 10,000 widgets are left after
    the other tests. `qtbot.waitUntil` deletes them all in its first wait, which may
    use up the whole timeout before the retry timer fires.
    """
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

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

    _delete_widgets_of_previous_tests()
    tester = JobWidgetTester(QReconstructViewer(job_dir), job_dir)
    widget = tester.widget
    qtbot.addWidget(widget)
    widget.show()
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

def test_reconstruct_particle_widget_hidden(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    star_text = Path(jobs_dir_tomo / "Reconstruct" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Reconstruct")

    _delete_widgets_of_previous_tests()
    tester = JobWidgetTester(QReconstructViewer(job_dir), job_dir)
    widget = tester.widget
    tab_widget = QtW.QTabWidget()
    qtbot.addWidget(tab_widget)
    tab_widget.addTab(widget, "Results")
    tab_widget.addTab(QtW.QWidget(), "Others")
    tab_widget.show()
    assert widget.isVisible()

    # a retry is postponed while hidden
    tester.mkdir("temp")
    fp = job_dir.path / "temp" / "sum_2_data_half0.mrc"
    with mrcfile.new(fp) as mrc:
        mrc.set_data(tester.make_random_mrc((64, 32, 17)))
    content = fp.read_bytes()
    fp.write_bytes(content[: len(content) // 2])
    widget.on_job_updated(job_dir, str(fp))
    assert widget._retry_timer.isActive()
    tab_widget.setCurrentIndex(1)
    assert not widget.isVisible()
    widget._retry_timer.setInterval(10)
    qtbot.waitUntil(lambda: widget._job_dir_to_update is not None, timeout=3000)
    assert not widget._retry_timer.isActive()
    assert not widget._viewer.has_image

    # loaded when shown
    fp.write_bytes(content)
    tab_widget.setCurrentIndex(0)
    assert widget._viewer.has_image
    assert widget._job_dir_to_update is None
    assert widget._file_name_label.text().startswith("Intermediate")

    # update is postponed while hidden
    tab_widget.setCurrentIndex(1)
    tester.write_random_mrc("merged.mrc", (32, 32, 32))
    assert widget._job_dir_to_update is not None
    assert widget._file_name_label.text().startswith("Intermediate")
    tab_widget.setCurrentIndex(0)
    assert widget._job_dir_to_update is None
    assert widget._file_name_label.text() == "merged.mrc"

def test_reconstruct_particle_widget_batch_update(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    star_text = Path(jobs_dir_tomo / "Reconstruct" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Reconstruct")

    tester = JobWidgetTester(QReconstructViewer(job_dir), job_dir)
    widget = tester.widget
    qtbot.addWidget(widget)
    widget.show()
    loaded = []
    load_result = widget._load_result
    widget._load_result = lambda job_dir: (loaded.append(job_dir), load_result(job_dir))

    # files written at once are read only once
    tester.write_random_mrc("merged.mrc", (32, 32, 32))
    loaded.clear()
    widget.on_job_files_updated(
        job_dir,
        [
            job_dir.path / "merged.mrc",
            job_dir.path / "RELION_JOB_EXIT_SUCCESS",
            job_dir.path / "run.out",
        ],
    )
    assert len(loaded) == 1
    assert widget._viewer.has_image

    # unrelated files are ignored
    widget.on_job_files_updated(job_dir, [job_dir.path / "run.out"])
    assert len(loaded) == 1

def test_reconstruct_particle_widget_outdated_worker(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    star_text = Path(jobs_dir_tomo / "Reconstruct" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Reconstruct")

    tester = JobWidgetTester(QReconstructViewer(job_dir), job_dir)
    widget = tester.widget
    qtbot.addWidget(widget)
    widget.show()
    tester.write_random_mrc("merged.mrc", (32, 32, 32))
    assert widget._viewer.has_image

    # the running worker is stopped when a new one starts
    class FakeWorker:
        quitted = False

        def quit(self):
            self.quitted = True

    old_worker = FakeWorker()
    widget._worker = old_worker
    widget.initialize(job_dir)
    assert old_worker.quitted

    # values yielded by an outdated worker are ignored
    widget._on_read_finished(_ReadResult(widget._load_id - 1, job_dir, map_data=None))
    assert widget._viewer.has_image
    widget._on_read_finished(
        _ReadResult(widget._load_id - 1, job_dir, error=OSError("broken"))
    )
    assert not widget._retry_timer.isActive()

def test_reconstruct_particle_widget_in_thread(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
    monkeypatch,
):
    star_text = Path(jobs_dir_tomo / "Reconstruct" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Reconstruct")

    _delete_widgets_of_previous_tests()
    tester = JobWidgetTester(QReconstructViewer(job_dir), job_dir)
    widget = tester.widget
    qtbot.addWidget(widget)
    widget.show()
    monkeypatch.setattr(_impl_objects, "IS_TESTING", False)

    tester.mkdir("temp")
    tester.write_random_mrc("temp/sum_2_data_half1.mrc", (64, 32, 17))
    tester.write_random_mrc("temp/sum_2_ctf_half1.mrc", (32, 32, 17))
    tester.write_random_mrc("temp/sum_2_ctf_half0.mrc", (32, 32, 17))
    tester.write_random_mrc("temp/sum_2_data_half0.mrc", (64, 32, 17))
    qtbot.waitUntil(lambda: widget._viewer.has_image, timeout=5000)
    assert widget._file_name_label.text().startswith("Intermediate")
    qtbot.waitUntil(lambda: widget._worker is None, timeout=5000)

    tester.write_random_mrc("merged.mrc", (32, 32, 32))
    qtbot.waitUntil(
        lambda: widget._file_name_label.text() == "merged.mrc", timeout=5000
    )
    qtbot.waitUntil(lambda: widget._worker is None, timeout=5000)
