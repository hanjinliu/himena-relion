from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator
from pytest import fixture
from qtpy.QtWidgets import QApplication
import gc

if TYPE_CHECKING:
    from himena_relion._job_dir import JobDirectory

@fixture(autouse=True, scope="session")
def import_all():
    """This is needed to initialize everything."""
    from himena_relion import relion5, relion5_tomo, external, io  # noqa: F401
    from himena_relion._impl_objects import set_is_testing
    from himena_relion._widgets._view_nd import QViewer

    set_is_testing(True)
    QViewer._always_force_sync = True

@fixture(scope="function")
def make_job_directory(tmpdir) -> "Iterator[Callable[[str], JobDirectory]]":
    from himena_relion._job_dir import JobDirectory

    project_dir = Path(tmpdir)

    def job_directory_factory(job_star_text: str, job_type: str = "Job") -> "JobDirectory":
        job_dir_path = project_dir / job_type / "job025"
        job_dir_path.mkdir(parents=True)
        star_path = job_dir_path / "job.star"
        star_path.write_text(job_star_text)
        return JobDirectory.from_job_star(star_path)

    yield job_directory_factory

    for _ in range(10):
        QApplication.processEvents()
    gc.collect()

@fixture(scope="function")
def jobs_dir_spa() -> Path:
    return Path(__file__).parent / "jobs_spa"

@fixture(scope="function")
def jobs_dir_tomo() -> Path:
    return Path(__file__).parent / "jobs_tomo"
