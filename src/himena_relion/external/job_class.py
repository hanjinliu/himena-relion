from abc import abstractmethod
import inspect
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Generator
from uuid import uuid4
from rich.console import Console
from importlib import import_module
from runpy import run_path
import starfile

from himena_relion import _job
from himena_relion._utils import last_job_directory
from himena_relion._job_class import RelionJob
from himena_relion.external.writers import prep_job_star


def pick_job_class(class_id: str) -> "type[RelionExternalJob]":
    """Pick the function to execute based on class_id."""

    if class_id.count(":") != 1:
        raise ValueError(f"Invalid class_id: {class_id}")
    class_file_path, class_name = class_id.split(":", 1)
    if class_file_path.endswith(".py"):
        ns = run_path(class_file_path)
        job_cls = ns[class_name]
    else:
        module = import_module(class_file_path)
        job_cls = getattr(module, class_name)
    if not issubclass(job_cls, RelionExternalJob):
        raise TypeError(f"Function {class_id} is not callable")
    return job_cls


class RelionExternalJob(RelionJob):
    def __init__(self, output_job_dir: _job.ExternalJobDirectory):
        self._output_job_dir = output_job_dir
        self._console = Console(record=True)
        cls = type(self)
        if pick_job_class(self.import_path()) is not cls:
            raise ValueError(
                "The return value of `import_path` cannot be used to pick "
                f"{cls!r} defined in {cls.__module__}:{cls.__name__}."
            )

    @property
    def output_job_dir(self) -> _job.ExternalJobDirectory:
        """Get the output job directory object."""
        return self._output_job_dir

    @property
    def console(self) -> Console:
        """Get the console object for logging."""
        return self._console

    @classmethod
    def import_path(cls) -> str:
        """Get the import path of the job class."""
        if cls.__module__ == "__main__":
            py_file_path = Path(inspect.getfile(cls)).as_posix()
            return f"{py_file_path}:{cls.__name__}"
        else:
            return f"{cls.__module__}:{cls.__name__}"

    @classmethod
    def himena_model_type(cls):
        import_path = cls.import_path()
        return import_path.replace(":", "-").replace("/", "-").replace(".", "-")

    @classmethod
    def job_title(cls) -> str:
        """Get the job title."""
        return cls.__name__

    @classmethod
    def create_and_run_job(
        cls,
        *args,
        **kwargs,
    ) -> str:
        import_path = cls.import_path()
        sig = cls._signature()
        bound = sig.bind(*args, **kwargs)  # Validate arguments
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            job_star_path = str(tmpdir / f"{uuid4()}.star")
            job_star_df = prep_job_star(import_path, **bound.arguments)
            starfile.write(job_star_df, job_star_path)
            subprocess.run(
                [
                    "relion_pipeliner",
                    "--addJobFromStar",
                    job_star_path,
                ]
            )
        d = last_job_directory()
        subprocess.Popen(["relion_pipeliner", "--RunJobs", d])
        return d

    @abstractmethod
    def output_nodes(self) -> list[tuple[str, str]]:
        """List of output nodes produced by this job.

        Examples
        --------
        ```python
        def output_nodes(self):
            return [
                ("tomograms.star", "TomogramGroupMetadata.star"),
            ]
        ```
        """

    @abstractmethod
    def run(self, *args, **kwargs) -> Generator[None, None, None]:
        """Run this job."""

    @classmethod
    def command_id(cls) -> str:
        """Get the command ID for this job."""
        return f"himena-relion:external:{cls.import_path()}"

    def provide_widget(self, job_dir: _job.ExternalJobDirectory) -> Any:
        """Provide a Qt widget for displaying the job results."""
        return NotImplemented

    @classmethod
    def _signature(cls) -> inspect.Signature:
        return inspect.signature(cls.run.__get__(object()))
