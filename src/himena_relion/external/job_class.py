from __future__ import annotations

from abc import ABC, abstractmethod
import inspect
from typing import Any, Generator
from rich.console import Console
from importlib import import_module
from runpy import run_path

from himena_relion import _job
from himena_relion._utils import unwrapped_annotated
from himena_relion.external.typemap import parse_string


def pick_job_class(class_id: str) -> type[RelionExternalJob]:
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


class RelionExternalJob(ABC):
    def __init__(self, output_job_dir: _job.ExternalJobDirectory):
        self._output_job_dir = output_job_dir
        self._console = Console(record=True)

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

    def job_title(self) -> str:
        """Get the job title."""
        return type(self).__name__

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

    def _parse_args(self, args: dict[str, Any]) -> dict[str, Any]:
        sig = inspect.signature(self.run)
        func_args = {}
        for param in sig.parameters.values():
            if param.name in args:
                arg = args.pop(param.name)
                annot = unwrapped_annotated(param.annotation)
                arg_parsed = parse_string(arg, annot)
                func_args[param.name] = arg_parsed
            elif param.default is param.empty:
                raise ValueError(f"Missing required argument: {param.name}")
            else:
                func_args[param.name] = param.default
        return func_args

    def _signature(self) -> inspect.Signature:
        return inspect.signature(self.run)
