from __future__ import annotations

from abc import abstractmethod
import inspect
import sys
from pathlib import Path
from typing import Any, Callable, Generator
from rich.console import Console
from importlib import import_module
from runpy import run_path

from himena.plugins import register_function

# NOTE: these must be imported at runtime, to inject the arguments of the commands
from himena.types import AnyContext
from himena.widgets import MainWindow
from himena_relion import _job_dir
from himena_relion._job_class import (
    RelionJob,
    connect_jobs,
    parse_string,
    show_scheduler_for_continue,
    _schedule_existing_job,
    _job_dir_from_path,
    _JOB_DIR_ARGS_NAME,
)
from himena_relion._utils import unwrap_annotated
from himena_relion.consts import ARG_NAME_REMAP
from himena_relion.external.writers import prep_job_star_external
from himena_relion.schemas import JobStarModel

# Parameters of the input nodes. These cannot be changed when continuing the job.
_INPUT_NODE_PARAMS = (
    "in_3dref",
    "in_coords",
    "in_mask",
    "in_mics",
    "in_movies",
    "in_parts",
)
# job options that are kept when continuing the job (not given by the parameters)
_OPTIONS_KEPT_ON_CONTINUE = (
    "do_queue",
    "min_dedicated",
    "other_args",
    "qsub",
    "qsubscript",
    "queuename",
)


def pick_job_class(class_id: str) -> type[RelionExternalJob] | None:
    """Pick the function to execute based on class_id."""

    if class_id.count(":") != 1:
        raise ValueError(f"Invalid class_id: {class_id}")
    if job_cls := _SINGLE_FILE_JOB_CLASSES.get(class_id):
        return job_cls
    class_file_path, class_name = class_id.split(":", 1)
    if class_file_path.endswith(".py"):
        ns = run_path(class_file_path)
        job_cls = ns.get(class_name, None)
    else:
        module = import_module(class_file_path)
        job_cls = getattr(module, class_name, None)
    if job_cls is None:
        # this case can happen when an himena-relion external job was installed and
        # executed, but later the plugin was uninstalled.
        return
    if not issubclass(job_cls, RelionExternalJob):
        raise TypeError(f"Function {class_id} is not callable")
    return job_cls


# _SINGLE_FILE_JOB_CLASSES is needed for the case when the job class is defined in a
# single .py file, which cannot be imported as a module.
_SINGLE_FILE_JOB_CLASSES: dict[str, type[RelionExternalJob]] = {}


class RelionExternalJob(RelionJob):
    """Abstract class for RELION external jobs.

    Must define `output_nodes` and `run` methods. To continue the jobs of this class,
    define subclasses of `RelionExternalContinue`.
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

    def input_edges(self, **kwargs) -> list[str]:
        sig = inspect.signature(self.run)
        out = []
        # job.star uses different names for some inputs (e.g. "in_mic" for "in_mics")
        arg_map = dict(ARG_NAME_REMAP)
        for param in sig.parameters.values():
            if param.name in _INPUT_NODE_PARAMS:
                remapped = arg_map.get(param.name, param.name)
                if edge := kwargs.get(param.name, "") or kwargs.get(remapped, ""):
                    out.append(edge)
        return out

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
            *_INPUT_NODE_PARAMS,
            "min_dedicated",
            "j",
            "other_args",
        ]:
            if key not in params:
                kwargs.pop(key, None)
        return kwargs

    def _log_job_version_info(self):
        job_cls = type(self)
        mod_str = job_cls.__module__.split(".")[0]
        if (mod := sys.modules.get(mod_str, None)) is not None:
            if _job_version := getattr(mod, "__version__", ""):
                self.console.log(f"Using {mod_str} v{_job_version}")
                return
        self.console.log("Version info not found for this job.")


class RelionExternalContinue(RelionExternalJob):
    """Abstract class to continue an existing RELION external job.

    This is the "Continue" of the RELION GUI for external jobs. Subclasses must define
    `original_class`, the external job class to continue, and the `run` method.
    Multiple continue classes can be defined for one job class.

    - The parameters of `run` are shown in the scheduler to continue the job, with the
      values of the job being continued.
    - `run` can have parameters that are not in `original_class.run`, such as the
      number of additional iterations. They are written to job.star only when the job
      is continued by this class. Their values are the ones of the last continue, or
      the defaults.
    - The input nodes (`in_parts` etc.) cannot be changed, as in the RELION GUI. They
      must be parameters of `original_class.run`.
    - The continued job.star has `rlnJobIsContinue = 1` and the executable of this
      class, so that `run` of this class is run in the same job directory. The job
      directory is still a job of `original_class`.

    Examples
    --------
    ```python
    class MyJob(RelionExternalJob):
        def run(self, in_parts, niter: int = 10):
            ...

    class MyJobContinue(RelionExternalContinue):
        original_class = MyJob

        # `niter_more` is a parameter only for continuing
        def run(self, in_parts, niter_more: int = 5):
            ...  # continue from the files left in the job directory
    ```
    """

    original_class: type[RelionExternalJob]

    def __init_subclass__(cls):
        super().__init_subclass__()
        if cls.__name__.startswith("_"):
            return  # abstract classes
        _check_continue_class(cls)
        _register_continue_command(cls)

    @abstractmethod
    def run(self, *args, **kwargs) -> Generator[None, None, None] | None:
        """Run the continued job in the same job directory.

        This method is called with the parameters of the job being continued, which may
        have been changed when continuing the job.
        """

    @classmethod
    def _is_continue_job(cls) -> bool:
        return True

    @classmethod
    def command_palette_title_prefix(cls) -> str:
        return "Continue -"

    @classmethod
    def job_title(cls) -> str:
        return cls.original_class.job_title()

    @classmethod
    def himena_model_type(cls) -> str:
        # the continued job directory is still a job of the original class
        return cls.original_class.himena_model_type()

    @classmethod
    def more_node_mappings(cls) -> dict[str | Callable[[Path], str], str]:
        """Define additional node mappings for this continue job, if needed."""
        return {}

    def output_nodes(self) -> list[tuple[str, str]]:
        """Continued job has the same output nodes as the original job by default."""
        return self._original_job().output_nodes()

    def input_edges(self, **kwargs) -> list[str]:
        """Continued job has the same input edges as the original job."""
        return self._original_job().input_edges(**kwargs)

    def provide_widget(self, job_dir: _job_dir.ExternalJobDirectory) -> Any:
        return self._original_job().provide_widget(job_dir)

    @classmethod
    def setup_widgets(cls, widgets):
        # the input nodes cannot be changed, as in the RELION GUI
        for name in _INPUT_NODE_PARAMS:
            if (widget := widgets.get(name)) is not None:
                widget.enabled = False

    @classmethod
    def _show_scheduler_widget_for_continue(
        cls,
        ui: MainWindow,
        context: AnyContext,
    ):
        # NOTE: `ui` and `context` are injected by the annotations
        return show_scheduler_for_continue(
            ui, cls, context, cls.original_class.normalize_kwargs_inv
        )

    def _original_job(self) -> RelionExternalJob:
        return self.original_class(self.output_job_dir)

    def make_job_star(self, **kwargs) -> JobStarModel:
        """Make the job.star to continue the job with the updated parameters.

        Parameters not given in `kwargs` and the input nodes are taken from the current
        job.star. Parameters only defined in this class are added to the parameters of
        the original job. Job options that are not parameters, such as the queue
        settings, are also kept.
        """
        orig_cls = self.original_class
        cont_params = type(self)._signature().parameters
        job_dir = self.output_job_dir
        job_star_old = JobStarModel.validate_file(job_dir.job_star())
        job_kwargs = orig_cls.normalize_kwargs_inv(**job_dir.get_job_params_as_dict())
        params = orig_cls._parse_args(dict(job_kwargs))
        # Parameters only for continuing. The value of the last continue is used if this
        # job was already continued with the parameter, as RELION does.
        for name, param in cont_params.items():
            if name in params:
                continue
            if name in job_kwargs:
                annot = unwrap_annotated(param.annotation)
                params[name] = parse_string(job_kwargs[name], annot)
            elif param.default is not param.empty:
                params[name] = param.default
        changeable = set(cont_params) - set(_INPUT_NODE_PARAMS)
        params.update({k: v for k, v in kwargs.items() if k in changeable})
        if missing := [name for name in cont_params if name not in params]:
            raise ValueError(f"Missing required arguments to continue: {missing}.")

        # RELION runs this class to continue the job. The parameter slots are made from
        # scratch, so that parameters of other continue jobs are not passed.
        values = prep_job_star_external(
            fn_exe=f"himena-relion {type(self).import_path()}",
            **params,
        ).joboptions_values.to_dict()
        for key, value_old in job_star_old.joboptions_values.to_dict().items():
            if key not in values or key in _OPTIONS_KEPT_ON_CONTINUE:
                values[key] = value_old
        return JobStarModel(
            job=JobStarModel.Job(
                job_type_label=job_star_old.job.job_type_label,
                job_is_continue=1,
                job_is_tomo=job_star_old.job.job_is_tomo,
            ),
            joboptions_values=JobStarModel.Options(
                variable=list(values.keys()),
                value=list(values.values()),
            ),
        )

    def continue_job(self, **kwargs) -> None:
        """Continue the job with updated parameters.

        job.star is updated by `make_job_star` and the job is scheduled. The pipeline
        watcher runs the job by `relion_pipeliner`, which runs `run` of this class.
        """
        # `kwargs` come from the scheduler widget. Argument names are not complete.
        self.prerun_check(**kwargs)
        job_star = self.make_job_star(**kwargs)
        _schedule_existing_job(self, job_star, kwargs, remove_exit_files=True)


def _check_continue_class(cls: type[RelionExternalContinue]) -> None:
    orig = getattr(cls, "original_class", None)
    if not (
        isinstance(orig, type)
        and issubclass(orig, RelionExternalJob)
        and not issubclass(orig, RelionExternalContinue)
    ):
        raise TypeError(
            f"{cls.__name__}.original_class must be an external job class to continue, "
            f"got {orig!r}."
        )
    # parameters that are not in the original job are allowed, except for the input
    # nodes, which belong to the original job and cannot be changed.
    orig_params = orig._signature().parameters
    for name in cls._signature().parameters:
        if name in _INPUT_NODE_PARAMS and name not in orig_params:
            raise TypeError(
                f"Input node {name!r} of {cls.__name__}.run is not a parameter of "
                f"{orig.__name__}.run. Input nodes cannot be added when continuing."
            )


def _register_continue_command(cls: type[RelionExternalContinue]) -> None:
    """Register the command to continue the job, suggested from the job window."""
    register_function(
        cls._show_scheduler_widget_for_continue,
        menus=[],
        title=f"{cls.command_palette_title_prefix()} {cls.job_title()}",
        command_id=cls.command_id(),
        palette=False,
        tooltip=cls.__doc__ or "Continue this job",
    )
    connect_jobs(
        cls.original_class,
        cls,
        node_mapping=cls.more_node_mappings(),
        other_context={_JOB_DIR_ARGS_NAME: _job_dir_from_path},
    )
