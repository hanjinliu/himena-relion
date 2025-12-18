from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import inspect
import logging
import subprocess
import tempfile
from typing import Any, Generator, get_origin
from pathlib import Path

from himena.types import AnyContext
from himena.workflow import WorkflowStep
from himena.widgets import MainWindow
from himena.plugins import when_reader_used, register_function
import pandas as pd
import starfile
from himena_relion import _job, _configs
from himena_relion._pipeline import RelionPipeline
from himena_relion.consts import Type, MenuId, JOB_ID_MAP
from himena_relion._utils import last_job_directory, unwrapped_annotated

_LOGGER = logging.getLogger(__name__)


class RelionJob(ABC):
    def __init__(self, output_job_dir: _job.JobDirectory):
        self._output_job_dir = output_job_dir

    @property
    def output_job_dir(self) -> _job.ExternalJobDirectory:
        """Get the output job directory object."""
        return self._output_job_dir

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
    def himena_model_type(cls):
        """Get the himena model type for this job."""

    @classmethod
    @abstractmethod
    def job_title(cls) -> str:
        """Get the job title."""

    @abstractmethod
    def run(self, *args, **kwargs) -> Generator[None, None, None]:
        """Run this job."""

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
            title=cls.job_title(),
            command_id=cls.command_id(),
        )

    @classmethod
    def create_and_run_job(cls, **kwargs) -> RelionJobExecution | None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            job_star_path = str(tmpdir / "job.star")
            job_star_df = cls.prep_job_star(**kwargs)
            starfile.write(job_star_df, job_star_path)
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
            # run the job
            proc = subprocess.Popen(
                ["relion_pipeliner", "--RunJobs", d],
                start_new_session=True,
            )
            return RelionJobExecution(proc, _job.JobDirectory(Path(d).resolve()))

    @classmethod
    @abstractmethod
    def prep_job_star(cls, **kwargs) -> pd.DataFrame:
        """Prepare job star data with given parameters."""

    def edit_and_run_job(self, **kwargs) -> RelionJobExecution | None:
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


class _RelionBuiltinJob(RelionJob):
    @classmethod
    def command_id(cls) -> str:
        return cls.type_label()

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        """Normalize the keyword arguments for this job."""
        # This is used to convert python to job.star
        kwargs.update(_configs.get_queue_dict())
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        # This is used to convert job.star to python, such as editing existing jobs
        for key in _configs.get_queue_dict().keys():
            kwargs.pop(key, None)
        kwargs.pop("scratch_dir", None)
        kwargs.pop("other_args", None)
        return kwargs

    @classmethod
    def job_title(cls) -> str:
        return JOB_ID_MAP.get(cls.type_label(), "Unknown")

    @classmethod
    def himena_model_type(cls):
        return cls.type_label()

    @classmethod
    def prep_job_star(cls, **kwargs):
        return prep_builtin_job_star(
            type_label=cls.type_label(),
            kwargs=cls.normalize_kwargs(**kwargs),
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
    job_directory: _job.JobDirectory


def iter_relion_jobs() -> Generator[type[RelionJob], None, None]:
    for cls in RelionJob.__subclasses__():
        if not (
            cls.__name__.startswith("_")
            or cls.__name__ == "RelionExternalJob"
            or cls is RelionJob
        ):
            yield cls
        yield from _iter_subclasses_recursive(cls)


def _iter_subclasses_recursive(cls: type) -> Generator[type, None, None]:
    for subclass in cls.__subclasses__():
        yield subclass
        yield from _iter_subclasses_recursive(subclass)


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
            raise ValueError(f"Cannot parse boolean from string: {s}")
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
    node_mapping: dict[str, str],
):
    type_pre = Type.RELION_JOB + "." + pre.himena_model_type()
    when = when_reader_used(type_pre, "himena_relion.io.read_relion_job")
    when.add_command_suggestion(
        post.command_id(),
        user_context=_node_mapping_to_context(node_mapping),
    )


def _node_mapping_to_context(node_mapping: dict[str, str]):
    def _func(ui: MainWindow, step: WorkflowStep) -> dict[str, Any]:
        win = ui.window_for_id(step.id)
        if win is None:
            return {}
        val = win.value
        if not isinstance(val, _job.JobDirectory):
            return {}
        # NOTE: the from_ file does NOT have to exist at this point.
        out = {}
        rln_dir = val.relion_project_dir
        for from_, to_ in node_mapping.items():
            file_path = val.path.joinpath(from_)
            out[to_] = file_path.relative_to(rln_dir).as_posix()
        return out

    return _func
