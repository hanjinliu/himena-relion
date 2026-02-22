from abc import abstractmethod
import inspect
from pathlib import Path
from typing import Any, Generator
from rich.console import Console
from importlib import import_module
from runpy import run_path

from himena_relion import _job_dir
from himena_relion._job_class import RelionJob
from himena_relion.consts import ARG_NAME_REMAP
from himena_relion.external.writers import prep_job_star_external
from himena_relion.schemas import JobStarModel


def pick_job_class(class_id: str) -> "type[RelionExternalJob]":
    """Pick the function to execute based on class_id."""

    if class_id.count(":") != 1:
        raise ValueError(f"Invalid class_id: {class_id}")
    if job_cls := _SINGLE_FILE_JOB_CLASSES.get(class_id):
        return job_cls
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


# _SINGLE_FILE_JOB_CLASSES is needed for the case when the job class is defined in a
# single .py file, which cannot be imported as a module.
_SINGLE_FILE_JOB_CLASSES: "dict[str, type[RelionExternalJob]]" = {}


class RelionExternalJob(RelionJob):
    """Abstract class for RELION external jobs.

    Must define `output_nodes` and `run` methods.
    """

    def __init__(self, output_job_dir: _job_dir.ExternalJobDirectory):
        super().__init__(output_job_dir)
        self._console = Console(record=True)
        cls = type(self)
        if pick_job_class(self.import_path()) is not cls:
            raise ValueError(
                "The return value of `import_path` cannot be used to pick "
                f"{cls!r} defined in {cls.__module__}:{cls.__name__}."
            )

    def __init_subclass__(cls):
        super().__init_subclass__()
        _SINGLE_FILE_JOB_CLASSES[cls.import_path()] = cls

    @property
    def output_job_dir(self) -> _job_dir.ExternalJobDirectory:
        """Get the output job directory object."""
        return self._output_job_dir

    @classmethod
    def command_palette_title_prefix(cls) -> str:
        return "RELION External:"

    @property
    def console(self) -> Console:
        """Get the console object for logging."""
        return self._console

    @classmethod
    def type_label(cls) -> str:
        return "relion.external"

    @classmethod
    def import_path(cls) -> str:
        """Get the import path of the job class."""
        if cls.__module__ == "__main__":
            raise ValueError(
                f"Job class {cls.__name__} is defined in __main__, which is not "
                "importable. Please define it in a separate .py file."
            )
        elif cls.__module__ == "<run_path>":
            py_file_path = Path(inspect.getfile(cls.run)).as_posix()
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
    def prep_job_star(cls, **kwargs) -> JobStarModel:
        import_path = cls.import_path()
        sig = cls._signature()
        bound = sig.bind(**kwargs)
        return prep_job_star_external(
            fn_exe=f"himena-relion {import_path}",
            **bound.arguments,
        )

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

    def provide_widget(self, job_dir: _job_dir.ExternalJobDirectory) -> Any:
        """Provide a Qt widget for displaying the job results."""
        return NotImplemented

    @classmethod
    def _signature(cls) -> inspect.Signature:
        from himena_relion import _annotated as _a

        sig = inspect.signature(cls.run.__get__(object()))
        param_normed = {}
        for param in sig.parameters.values():
            if param.annotation is param.empty:
                match param.name:
                    case "in_3dref":
                        annot = _a.io.MAP_TYPE
                    case "in_coords":
                        annot = _a.io.IN_COORDINATES
                    case "in_mask":
                        annot = _a.io.IN_MASK
                    case "in_mics":
                        annot = _a.io.IN_MICROGRAPHS
                    case "in_movies":
                        annot = _a.io.IN_MOVIES
                    case "in_parts":
                        annot = _a.io.IN_PARTICLES
                    case "min_dedicated":
                        annot = _a.running.MIN_DEDICATED
                    case "j":
                        annot = _a.running.NR_THREADS
                    case _:
                        raise TypeError(
                            f"Parameter {param.name!r} of {cls.__name__}.run must have "
                            "a type annotation."
                        )
                param = inspect.Parameter(
                    name=param.name,
                    kind=param.kind,
                    default=param.default,
                    annotation=annot,
                )
            param_normed[param.name] = param

        return inspect.Signature(
            parameters=param_normed.values(),
            return_annotation=sig.return_annotation,
        )

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        params = cls._signature().parameters
        for correct, wrong in ARG_NAME_REMAP:
            if wrong in kwargs and correct not in kwargs:
                kwargs[correct] = kwargs.pop(wrong)
        for key in [
            "fn_exe",
            "do_queue",
            "in_3dref",
            "in_coords",
            "in_mask",
            "in_mics",
            "in_movies",
            "in_parts",
            "min_dedicated",
            "j",
            "other_args",
        ]:
            if key not in params:
                kwargs.pop(key, None)
        return kwargs
