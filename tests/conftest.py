from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator
from pytest import fixture
from qtpy.QtCore import QEvent
from qtpy.QtWidgets import QApplication
import gc

if TYPE_CHECKING:
    from himena_relion._job_dir import JobDirectory
    from ._fake_relion import FakeRelionPipeliner

@fixture(autouse=True, scope="session")
def import_all():
    """This is needed to initialize everything."""
    from himena_relion import relion5, relion5_tomo, external, io  # noqa: F401
    from himena_relion._impl_objects import set_is_testing
    from himena_relion._widgets._view_nd import QViewer

    set_is_testing(True)
    QViewer._always_force_sync = True

@fixture(autouse=True)
def fixed_relion_version(monkeypatch):
    """Test data are created by RELION 5.0. Do not depend on the installed RELION
    (or the one in WSL)."""
    from himena_relion import _version

    monkeypatch.setattr(
        _version, "relion_version", lambda: "RELION version: 5.0.0-commit-000000"
    )

@fixture(scope="function")
def make_job_directory(tmpdir) -> "Iterator[Callable[[str], JobDirectory]]":
    from himena_relion._job_dir import JobDirectory

    project_dir = Path(tmpdir)

    def job_directory_factory(job_star_text: str, job_type: str = "Refine3D") -> "JobDirectory":
        if "/" in job_type:
            job_dir_path = project_dir / job_type
        else:
            job_dir_path = project_dir / job_type / "job025"
        job_dir_path.mkdir(parents=True)
        star_path = job_dir_path / "job.star"
        star_path.write_text(job_star_text)
        return JobDirectory.from_job_star(star_path)

    yield job_directory_factory

    for _ in range(10):
        QApplication.processEvents()
    gc.collect()

@fixture(autouse=True)
def delete_widgets_later():
    """Delete the widgets scheduled for deletion (`deleteLater`) after each test.

    `QApplication.processEvents` does not delete them, so they are left until an event
    loop runs, such as `qtbot.wait`. Without this, more than 10,000 widgets were left
    during the test session, and deleting all of them in one `qtbot.waitUntil` could
    take longer than its timeout. The widgets added by `qtbot.addWidget` are closed
    before the fixtures are torn down, so they are deleted here too.
    """
    yield
    if QApplication.instance() is not None:
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

@fixture(autouse=True)
def no_detached_processes():
    """Do not carry the (possibly fake) processes over to the next test."""
    from himena_relion import _proc

    _proc._DETACHED_PROCESSES.clear()
    yield
    _proc._DETACHED_PROCESSES.clear()

@fixture(scope="function")
def jobs_dir_spa() -> Path:
    return Path(__file__).parent / "jobs_spa"

@fixture(scope="function")
def jobs_dir_tomo() -> Path:
    return Path(__file__).parent / "jobs_tomo"

@fixture
def in_project(tmp_path: Path, monkeypatch) -> Path:
    """A new RELION project directory, which is the current directory."""
    # jobs are identified by the paths relative to the project directory
    monkeypatch.chdir(tmp_path)
    return tmp_path

@fixture
def relion(in_project: Path, monkeypatch) -> "FakeRelionPipeliner":
    """Emulate `relion_pipeliner` in the project, instead of running RELION."""
    from himena_relion import _job_class, pipeline_watcher
    from ._fake_relion import FakeRelionPipeliner

    fake = FakeRelionPipeliner(in_project)
    monkeypatch.setattr(
        _job_class, "_run_relion_pipeliner_add_job_from_star", fake.add_job_from_star
    )
    monkeypatch.setattr(pipeline_watcher.subprocess, "Popen", fake.popen)
    # The watcher is not started as a new process. `check_scheduled_jobs` is called
    # instead.
    monkeypatch.setattr(_job_class, "run_watcher_new_process", lambda *_: None)
    return fake
