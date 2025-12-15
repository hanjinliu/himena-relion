from __future__ import annotations

from abc import ABC, abstractmethod
import inspect
from typing import Any, Generator
from rich.console import Console

from himena_relion import _job


class RelionExternalJobRegistry:
    def __init__(self):
        self._reg = {}

    def register(self, job_cls: type[RelionExternalJob]) -> None:
        self._reg[job_cls.import_path()] = job_cls

    def pick(self, import_path: str) -> type[RelionExternalJob] | None:
        return self._reg.get(import_path, None)


REGISTRY = RelionExternalJobRegistry()


class RelionExternalJob(ABC):
    def __init__(self, output_job_dir: _job.ExternalJobDirectory):
        self._output_job_dir = output_job_dir
        self._console = Console(record=True)

    def __init_subclass__(cls):
        REGISTRY.register(cls)
        return super().__init_subclass__()

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
            py_file_path = inspect.getfile(cls)
            return f"{py_file_path}:{cls.__name__}"
        else:
            return f"{cls.__module__}:{cls.__name__}"

    @classmethod
    def job_title(cls) -> str:
        """Get the job title."""
        return cls.__name__

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
    def run(self, *args, **kwargs) -> Generator[None, None, None]: ...

    def provide_widget(self, job_dir: _job.ExternalJobDirectory) -> Any:
        """Provide a Qt widget for displaying the job results."""
        return NotImplemented
