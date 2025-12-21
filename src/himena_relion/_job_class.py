from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import inspect
import logging
import subprocess
import tempfile
from typing import Any, Callable, Generator, get_origin
from pathlib import Path
from magicgui.widgets.bases import ValueWidget

from himena.types import AnyContext
from himena.workflow import WorkflowStep
from himena.widgets import MainWindow
from himena.plugins import when_reader_used, register_function
import pandas as pd
import starfile
from himena_relion import _configs, _job_dir
from himena_relion._pipeline import RelionPipeline
from himena_relion.consts import Type, MenuId, JOB_ID_MAP
from himena_relion._utils import (
    last_job_directory,
    unwrapped_annotated,
    change_name_for_tomo,
)

_LOGGER = logging.getLogger(__name__)


class RelionJob(ABC):
    """Class that describes a RELION job.

    Each RELION job directory is represented as instantiation of a subclass of this
    class. That's why most of the methods are classmethods.

    Running a job is defined by the `run` method, although it does not necesarrily
    implement the actual running of the job (because RELION runs jobs externally).
    """

    def __init__(self, output_job_dir: _job_dir.JobDirectory):
        self._output_job_dir = output_job_dir

    @property
    def output_job_dir(self) -> _job_dir.ExternalJobDirectory:
        """Get the output job directory object."""
        return self._output_job_dir

    @classmethod
    def command_palette_title_prefix(cls) -> str:
        return "RELION:"

    @classmethod
    @abstractmethod
    def type_label(cls) -> str:
        """Get the type label for this builtin job."""

    @classmethod
    @abstractmethod
    def command_id(cls) -> str:
        """Get the command ID for this job."""

    @classmethod
    @abstractmethod
    def himena_model_type(cls) -> str:
        """Get the himena model type for this job."""

    @classmethod
    @abstractmethod
    def job_title(cls) -> str:
        """Get the job title."""

    @abstractmethod
    def run(self, *args, **kwargs) -> Generator[None, None, None]:
        """Run this job."""

    @classmethod
    def setup_widgets(self, widgets: dict[str, ValueWidget]):
        """Setup the magicgui widgets for this job.

        This methods is called after all the widgets are created.
        """

    @classmethod
    def _signature(cls) -> inspect.Signature:
        return inspect.signature(cls.run.__get__(object()))

    @classmethod
    def _parse_args(cls, args: dict[str, Any]) -> dict[str, Any]:
        sig = cls._signature()
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

    def __init_subclass__(cls):
        """This is called when a subclass is defined.

        All the RELION external jobs defined this way will be automatically registered.
        """
        if cls.__name__.startswith("_") or cls.__name__ == "RelionExternalJob":
            return
        _LOGGER.info(
            "Registering RELION job %s with command ID %s",
            cls.job_title(),
            cls.command_id(),
        )
        register_function(
            cls._show_scheduler_widget,
            menus=[MenuId.RELION_NEW_JOB],
            title=f"{cls.command_palette_title_prefix()} {cls.job_title()}",
            command_id=cls.command_id(),
        )

    @classmethod
    def create_and_run_job(cls, **kwargs) -> RelionJobExecution | None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            job_star_path = str(tmpdir / "job.star")
            job_star_df = cls.prep_job_star(**kwargs)
            starfile.write(job_star_df, job_star_path)
            # $ relion_pipeliner --addJobFromStar <job.star>
            # This reformats the input job.star and creates a new job directory.
            # The new job is scheduled but NOT run yet. To run the job, we need to
            # call relion_pipeliner --RunJobs <job_dir>
            subprocess.run(
                [
                    "relion_pipeliner",
                    "--addJobFromStar",
                    job_star_path,
                ],
                check=True,
            )
        d = last_job_directory()
        # check if all the input is ready
        pipeline = RelionPipeline.from_star(Path(d) / "job_pipeline.star")
        inputs_ready = all(input_.path.exists() for input_ in pipeline.inputs)

        if inputs_ready:
            # Run the job. Note that the job path must be in "Class3D/job012/" format.
            proc = subprocess.Popen(
                ["relion_pipeliner", "--RunJobs", d],
                start_new_session=True,
            )
            return RelionJobExecution(proc, _job_dir.JobDirectory(Path(d).resolve()))

    @classmethod
    @abstractmethod
    def prep_job_star(cls, **kwargs) -> dict[str, Any]:
        """Prepare job star data with given parameters."""

    def edit_and_run_job(self, **kwargs) -> RelionJobExecution | None:
        """Edit the existing job directory and run it."""
        job_dir = self.output_job_dir
        job_star_df = self.prep_job_star(**kwargs)
        starfile.write(job_star_df, job_dir.job_star())
        to_run = str(job_dir.path.relative_to(job_dir.relion_project_dir))
        if not to_run.endswith("/"):
            to_run += "/"
        pipeline = RelionPipeline.from_star(Path(to_run, "job_pipeline.star"))
        inputs_ready = all(input_.path.exists() for input_ in pipeline.inputs)
        if inputs_ready:
            proc = subprocess.Popen(
                ["relion_pipeliner", "--RunJobs", to_run],
                start_new_session=True,
            )
            return RelionJobExecution(proc, job_dir)

    @classmethod
    def _show_scheduler_widget(cls, ui: MainWindow, context: AnyContext):
        from himena_relion._widgets._job_edit import QJobScheduler

        for dock in ui.dock_widgets:
            if isinstance(scheduler := dock.widget, QJobScheduler):
                dock.show()
                break
        else:
            scheduler = QJobScheduler(ui)
            ui.add_dock_widget(scheduler, title="RELION Job Scheduler", area="right")
        scheduler.update_by_job(cls)
        if context:
            scheduler.set_parameters(context)
        scheduler.set_schedule_mode()
        return scheduler

    @classmethod
    def job_is_tomo(cls) -> bool:
        """Return whether this job is a tomogram job."""
        # Jobs defined in relion --tomo gui does NOT mean that they are always tomo
        # jobs.
        return False

    @classmethod
    def param_matches(cls, job_params: dict[str, str]) -> bool:
        return True


class _RelionBuiltinJob(RelionJob):
    @classmethod
    def command_id(cls) -> str:
        return cls.type_label()

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        """Normalize the keyword arguments for this job.

        This is used to convert python objects to job.star.
        """
        kwargs.update(_configs.get_queue_dict())
        if "gpu_ids" in kwargs:
            gpu_ids = kwargs["gpu_ids"]
            assert isinstance(gpu_ids, str)
            kwargs["use_gpu"] = len(gpu_ids.strip()) > 0
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        """This is used to convert job.star to python, such as editing existing jobs."""
        for key in _configs.get_queue_dict().keys():
            kwargs.pop(key, None)
        kwargs.pop("scratch_dir", None)
        kwargs.pop("other_args", None)
        kwargs.pop("use_gpu", None)
        return kwargs

    @classmethod
    def job_title(cls) -> str:
        out = JOB_ID_MAP.get(cls.type_label(), "Unknown")
        return out

    @classmethod
    def himena_model_type(cls) -> str:
        out = cls.type_label()
        if cls.job_is_tomo():
            # NOTE: Unfortunately, some relion job uses the "rlnJobIsTomo" flag to
            # switch what to do, instead of defining a separate job type.
            # This implementation appends "_tomo" to the job type to distinguish them.
            # e.g. "relion.motioncor2" -> "relion.motioncor2_tomo"
            # e.g. "relion.motioncor2.own" -> "relion.motioncor2_tomo.own"
            # e.g. "relion.importtomo" -> "relion.importtomo"  (no change)
            out = change_name_for_tomo(out)
        return out

    @classmethod
    def prep_job_star(cls, **kwargs):
        return prep_builtin_job_star(
            type_label=cls.type_label(),
            kwargs=cls.normalize_kwargs(**kwargs),
            is_tomo=int(cls.job_is_tomo()),
        )


def prep_builtin_job_star(
    type_label: str, is_tomo: int = 0, kwargs: dict[str, Any] = {}
):
    job = {
        "rlnJobTypeLabel": type_label,
        "rlnJobIsContinue": 0,
        "rlnJobIsTomo": is_tomo,
    }
    _var = []
    _val = []
    for k, v in kwargs.items():
        _var.append(k)
        _val.append(to_string(v))
    joboptions_values = {
        "rlnJobOptionVariable": _var,
        "rlnJobOptionValue": _val,
    }
    return {
        "job": job,
        "joboptions_values": pd.DataFrame(joboptions_values),
    }


@dataclass
class RelionJobExecution:
    process: subprocess.Popen
    job_directory: _job_dir.JobDirectory


def iter_relion_jobs() -> Generator[type[RelionJob], None, None]:
    yield from _iter_subclasses_recursive(RelionJob)


def _iter_subclasses_recursive(cls: type) -> Generator[type, None, None]:
    for cls in cls.__subclasses__():
        if (
            cls.__name__.startswith("_")
            or cls.__name__ == "RelionExternalJob"
            or cls is RelionJob
        ):
            pass  # these classes are abstract or internal
        else:
            yield cls
        yield from _iter_subclasses_recursive(cls)


def _split_list_and_arg(typ: Any) -> tuple[Any, Any]:
    if getattr(typ, "__origin__", None) is list:
        args = typ.__args__
        if len(args) != 1:
            raise TypeError(f"Unsupported list type with multiple args: {typ}")
        return list, args[0]
    else:
        return typ, str


def parse_string(s: Any, typ: Any) -> Any:
    if isinstance(typ, str):
        raise TypeError("Type annotation cannot be a string instance")
    if typ is str:
        return s
    elif typ is int:
        return int(s)
    elif typ is float:
        return float(s)
    elif typ is bool:
        if s in ["0", "False", "false", "No"]:
            return False
        elif s in ["1", "True", "true", "Yes"]:
            return True
        else:
            return bool(s)
    elif typ is Path:
        return Path(s)
    elif get_origin(typ) is list:
        _, elem = _split_list_and_arg(typ)
        if isinstance(s, str):
            parts = s.split(",")
        else:
            parts = s
        return [parse_string(part, elem) for part in parts]
    elif get_origin(typ) is tuple:
        args = typ.__args__
        if isinstance(s, str):
            parts = s.split(",")
        else:
            parts = s
        if len(parts) != len(args):
            raise ValueError(
                f"Cannot parse tuple from string: {s}, expected {len(args)} elements"
            )
        return tuple(parse_string(part, arg) for part, arg in zip(parts, args))
    elif get_origin(typ) is dict or typ is dict:
        return dict(s)
    else:
        raise TypeError(f"Unsupported type for parsing: {typ}")


def to_string(value) -> str:
    if isinstance(value, Path):
        value = str(value)
    elif isinstance(value, bool):
        value = "Yes" if value else "No"
    return value


def connect_jobs(
    pre: type[RelionJob],
    post: type[RelionJob],
    node_mapping: dict[str | Callable[[Path], str], str] | None = None,
):
    type_pre = Type.RELION_JOB + "." + pre.himena_model_type()
    when = when_reader_used(type_pre, "himena_relion.io.read_relion_job")
    if node_mapping is None:
        user_context = None
    else:
        user_context = _node_mapping_to_context(node_mapping)
    when.add_command_suggestion(
        post.command_id(),
        user_context=user_context,
    )


def _node_mapping_to_context(node_mapping: dict[str | Callable[[Path], str], str]):
    def _func(ui: MainWindow, step: WorkflowStep) -> dict[str, Any]:
        win = ui.window_for_id(step.id)
        if win is None:
            return {}
        val = win.value
        if not isinstance(val, _job_dir.JobDirectory):
            return {}
        # NOTE: the from_ file does NOT have to exist at this point.
        out = {}
        rln_dir = val.relion_project_dir
        for from_, to_ in node_mapping.items():
            if isinstance(from_, str):
                file_path = val.path.joinpath(from_)
            elif callable(from_):
                file_path = Path(from_(val.path))
            else:
                raise TypeError(f"Unsupported from_ type: {type(from_)}")
            file_path_rel = file_path.relative_to(rln_dir).as_posix()
            if "." in to_:  # dict valule
                to_, subkey = to_.split(".", 1)
                if to_ not in out:
                    out[to_] = {}
                out[to_][subkey] = file_path_rel
            else:
                out[to_] = file_path_rel
        return out

    return _func
