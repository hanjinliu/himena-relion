from __future__ import annotations

from abc import ABC, abstractmethod
import inspect
from typing import Any, Generator, Callable, get_origin
from pathlib import Path

from himena import MainWindow
from himena.plugins import when_reader_used, register_function
from himena_relion.consts import Type, MenuId
from himena_relion._utils import unwrapped_annotated


class RelionJob(ABC):
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
        register_function(
            cls._show_scheduler_widget,
            menus=[MenuId.RELION_NEW_JOB],
            title=cls.job_title(),
            command_id=cls.command_id(),
        )

    @classmethod
    @abstractmethod
    def create_and_run_job(cls, **kwargs) -> str:
        """Create and run a job with the given parameters, returns the job directory."""

    @classmethod
    def _show_scheduler_widget(cls, ui: MainWindow):
        from himena_relion._widgets._job_edit import QJobScheduler

        for dock in ui.dock_widgets:
            if isinstance(scheduler := dock.widget, QJobScheduler):
                dock.show()
                break
        else:
            scheduler = QJobScheduler(ui)
            ui.add_dock_widget(scheduler, title="RELION Job Scheduler", area="right")
        scheduler.update_by_job(cls)


def _split_list_and_arg(typ: Any) -> tuple[Any, Any]:
    if getattr(typ, "__origin__", None) is list:
        args = typ.__args__
        if len(args) != 1:
            raise TypeError(f"Unsupported list type with multiple args: {typ}")
        return list, args[0]
    else:
        return typ, str


def parse_string(s: str, typ: Any) -> Any:
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
        return [parse_string(part, elem) for part in s.split(",")]
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
    when = when_reader_used(type_pre, "himena-relion.io.read_relion_job")
    when.add_command_suggestion(
        Type.RELION_JOB + "." + post.himena_model_type(),
        defaults=_node_mapping_to_defaults(node_mapping, source_job=pre),
    )


def _node_mapping_to_defaults(
    node_mapping: dict[str, str],
    source_job: RelionJob,
):
    defaults: dict[str, Callable] = {}
    # TODO: implement this function
    return defaults
