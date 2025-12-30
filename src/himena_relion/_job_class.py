from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
import inspect
import logging
import subprocess
import tempfile
from types import NoneType, UnionType
from typing import (
    Any,
    Callable,
    Generator,
    Literal,
    Union,
    get_args,
    get_origin,
    TYPE_CHECKING,
)
from pathlib import Path
from magicgui.widgets.bases import ValueWidget

from himena.types import AnyContext, WidgetDataModel
from himena.workflow import WorkflowStep
from himena.widgets import MainWindow
from himena.plugins import when_reader_used, register_function
import numpy as np
from himena_relion import _configs, _job_dir
from himena_relion._pipeline import is_all_inputs_ready
from himena_relion.consts import Type, MenuId, JOB_ID_MAP
from himena_relion._utils import (
    last_job_directory,
    unwrap_annotated,
    change_name_for_tomo,
    normalize_job_id,
    update_default_pipeline,
)
from himena_relion.schemas import JobStarModel

if TYPE_CHECKING:
    from himena_relion._widgets._job_edit import QJobScheduler

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
    def output_job_dir(self) -> _job_dir.JobDirectory:
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
    def setup_widgets(cls, widgets: dict[str, ValueWidget]):
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
                annot = unwrap_annotated(param.annotation)
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
        if (
            cls.__name__.startswith("_")
            or cls.__name__ == "RelionExternalJob"
            or issubclass(cls, _RelionBuiltinContinue)
        ):
            return
        command_id = cls.command_id()
        _LOGGER.info(
            "Registering RELION job %s with command ID %s",
            cls.job_title(),
            command_id,
        )
        register_function(
            cls._show_scheduler_widget,
            menus=[MenuId.RELION_NEW_JOB],
            title=f"{cls.command_palette_title_prefix()} {cls.job_title()}",
            command_id=command_id,
            tooltip=getattr(cls, "__doc__", None),
        )

    @classmethod
    def create_and_run_job(cls, **kwargs) -> RelionJobExecution | None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            job_star_path = tmpdir / "job.star"
            job_star_model = cls.prep_job_star(**kwargs)

            job_star_model.write(job_star_path)
            # $ relion_pipeliner --addJobFromStar <job.star>
            # This reformats the input job.star and creates a new job directory.
            # The new job is scheduled but NOT run yet. To run the job, we need to
            # call relion_pipeliner --RunJobs <job_dir>
            args = ["relion_pipeliner", "--addJobFromStar", str(job_star_path)]
            proc = subprocess.run(args)
            if proc.returncode != 0:
                args_str = " ".join(args)
                raise RuntimeError(
                    f"{args_str} failed. Created job.star follows:"
                    f"\n\n{job_star_path.read_text()}"
                )

        d = last_job_directory()  # FIXME: not thread-safe
        if is_all_inputs_ready(d):
            return execute_job(d)

    @classmethod
    @abstractmethod
    def prep_job_star(cls, **kwargs) -> JobStarModel:
        """Prepare job star data with given parameters."""

    def edit_and_run_job(self, **kwargs) -> RelionJobExecution | None:
        """Edit the existing job directory and run it."""
        job_dir = self.output_job_dir
        job_star_model = self.prep_job_star(**kwargs)
        job_star_model.write(job_dir.job_star())
        to_run = str(job_dir.path.relative_to(job_dir.relion_project_dir))
        if is_all_inputs_ready(to_run):
            return execute_job(to_run)
        else:
            default_pipeline_path = job_dir.relion_project_dir / "default_pipeline.star"
            if not default_pipeline_path.exists():
                return _LOGGER.warning("Project default_pipeline.star not found.")
            # Job state needs to be updated to "Scheduled"
            update_default_pipeline(default_pipeline_path, to_run, state="Scheduled")

    @classmethod
    def _show_scheduler_widget(cls, ui: MainWindow, context: AnyContext):
        scheduler = _get_scheduler_widget(ui)
        try:
            scheduler.update_by_job(cls)
            if context:
                scheduler.set_parameters(context)
        finally:
            # this must be called even if update_by_job fails
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
        """Only used to dispatch existing jobs to the correct class."""
        return True

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        """This is used to convert python objects to job.star."""
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        """This is used to convert job.star to python, such as editing existing jobs."""
        return kwargs


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
        if "use_scratch" in kwargs:
            kwargs["scratch_dir"] = (
                _configs.get_scratch_dir() if kwargs.pop("use_scratch") else ""
            )
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        """This is used to convert job.star to python, such as editing existing jobs."""
        for key in _configs.get_queue_dict().keys():
            kwargs.pop(key, None)
        if "scratch_dir" in kwargs:
            kwargs["use_scratch"] = kwargs.pop("scratch_dir", "").strip() != ""
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
    def prep_job_star(cls, **kwargs) -> JobStarModel:
        _var = []
        _val = []
        for k, v in cls.normalize_kwargs(**kwargs).items():
            _var.append(k)
            _val.append(to_string(v))
        return JobStarModel(
            job=JobStarModel.Job(
                job_type_label=cls.type_label(),
                job_is_continue=int(issubclass(cls, _RelionBuiltinContinue)),
                job_is_tomo=int(cls.job_is_tomo()),
            ),
            joboptions_values=JobStarModel.Options(
                variable=_var,
                value=_val,
            ),
        )


class _RelionBuiltinContinue(_RelionBuiltinJob):
    original_class: type[RelionJob]

    @classmethod
    def command_id(cls) -> str:
        return cls.original_class.command_id() + ".continue"

    @classmethod
    def command_palette_title_prefix(cls) -> str:
        return "Continue -"

    @classmethod
    def type_label(cls) -> str:
        return cls.original_class.type_label()

    @classmethod
    def job_title(cls) -> str:
        return cls.original_class.job_title()

    def __init_subclass__(cls):
        """This is called when a subclass is defined.

        All the RELION external jobs defined this way will be automatically registered.
        """
        if cls.__name__.startswith("_") or cls.__name__ == "RelionExternalJob":
            return
        command_id = cls.command_id()
        _LOGGER.info(
            "Registering RELION job %s with command ID %s",
            cls.job_title(),
            command_id,
        )
        register_function(
            cls._show_scheduler_widget_for_continue,
            menus=[],
            title=f"{cls.command_palette_title_prefix()} {cls.job_title()}",
            command_id=command_id,
            palette=False,
        )

        # auto connect jobs
        connect_jobs(
            cls.original_class,
            cls,
            node_mapping=cls.more_node_mappings(),
        )

    @classmethod
    def more_node_mappings(cls) -> dict[str | Callable[[Path], str], str]:
        """Define additional node mappings for this continue job, if needed."""
        return {}

    @classmethod
    def _show_scheduler_widget_for_continue(
        cls,
        ui: MainWindow,
        model: WidgetDataModel,
        context: AnyContext,
    ):
        scheduler = _get_scheduler_widget(ui)
        try:
            scheduler.update_by_job(cls)
            job_dir = model.value
            if not isinstance(job_dir, _job_dir.JobDirectory):
                raise RuntimeError("Widget model does not contain a job directory.")
            orig_params = job_dir.get_job_params_as_dict()
            sig = cls._signature()
            for orig_key, orig_val in orig_params.items():
                if orig_key in sig.parameters:
                    context.setdefault(orig_key, orig_val)
            if context:
                scheduler.set_parameters(context)
        finally:
            scheduler.set_continue_mode(job_dir)
        return scheduler

    def continue_job(self, **kwargs) -> RelionJobExecution | None:
        """Continue this job with updated parameters."""
        job_dir = self.output_job_dir
        job_star_path = job_dir.job_star()
        job_star = JobStarModel.validate_file(job_star_path)
        params_df = job_star.joboptions_values.dataframe
        if job_cls := job_dir._to_job_class():
            kwargs = job_cls.normalize_kwargs(**kwargs)
        # update job parameters
        for key, val_new in kwargs.items():
            mask = job_star.joboptions_values.variable == key
            idx = np.where(mask)[0]
            if len(idx) == 1:
                params_df.iloc[idx[0], 1] = to_string(val_new)
        job_star.joboptions_values = params_df
        job_star.write(job_star_path)
        d = job_dir.path.relative_to(job_dir.relion_project_dir).as_posix()
        return execute_job(d)


@dataclass
class RelionJobExecution:
    process: subprocess.Popen
    job_directory: _job_dir.JobDirectory


def iter_relion_jobs() -> Generator[type[RelionJob], None, None]:
    # Used for finding the proper job class from existing job directories.
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
    orig = get_origin(typ)
    if orig in (Union, UnionType):
        args = get_args(typ)
        if len(args) == 2 and NoneType in args:
            # Union[T, None] or T | None
            non_none_type = args[0] if args[1] is NoneType else args[1]
            if s in ("", "None", None):
                return None
            return parse_string(s, non_none_type)
        else:
            raise TypeError(f"Unsupported Union type for parsing: {typ}")
    elif orig is Literal:
        return s  # just trust
    elif typ is str:
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
    elif orig is list:
        _, elem = _split_list_and_arg(typ)
        if isinstance(s, str):
            parts = s.split(",")
        else:
            parts = s
        return [parse_string(part, elem) for part in parts]
    elif orig is tuple:
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
    elif orig is dict or typ is dict:
        return dict(s)
    else:
        raise TypeError(f"Unsupported type for parsing: {typ}")


def to_string(value) -> str:
    if isinstance(value, Path):
        value = str(value)
    elif isinstance(value, bool):
        value = "Yes" if value else "No"
    return value


# For debugging purposes, such as drawing connection maps
CONNECTED_JOBS: list[tuple[type[RelionJob], type[RelionJob]]] = []


def connect_jobs(
    pre: type[RelionJob],
    post: type[RelionJob],
    node_mapping: dict[str | Callable[[Path], str], str] | None = None,
    value_mapping: dict[str | Callable[[Path], Any], Any] | None = None,
):
    CONNECTED_JOBS.append((pre, post))
    type_pre = Type.RELION_JOB + "." + pre.himena_model_type()
    when = when_reader_used(type_pre, "himena_relion.io.read_relion_job")
    user_context = _node_mapping_to_context(node_mapping, value_mapping)
    when.add_command_suggestion(
        post.command_id(),
        user_context=user_context,
    )


def execute_job(d: str | Path, ignore_error: bool = False) -> RelionJobExecution:
    """Execute a RELION job named `d` (such as "Class3D/job012/")."""
    d = normalize_job_id(d)
    try:
        job_dir = _job_dir.JobDirectory(Path(d).resolve())
    except FileNotFoundError as e:
        if not ignore_error:
            raise e
        _LOGGER.warning("Error executing RELION job %s", d, exc_info=True)
        return None
    args = ["relion_pipeliner", "--RunJobs", d]
    # NOTE: Because himena also uses Qt, RELION jobs that depend on napari (such as
    # ExcludeTiltSeries) may fail to start, saying no Qt bindings are available. This
    # seems to be due to environment variable QT_API being set to incompatible value
    # like "pyqt6".
    env = os.environ.copy()
    env.pop("QT_API", None)
    proc = subprocess.Popen(args, start_new_session=True, env=env)
    _LOGGER.info("Started RELION job %s with PID %d", d, proc.pid)
    return RelionJobExecution(proc, job_dir)


def _get_scheduler_widget(ui: MainWindow) -> QJobScheduler:
    from himena_relion._widgets._job_edit import QJobScheduler

    for dock in ui.dock_widgets:
        if isinstance(scheduler := dock.widget, QJobScheduler):
            dock.show()
            break
    else:
        scheduler = QJobScheduler(ui)
        ui.add_dock_widget(scheduler, title="RELION Job Scheduler", area="right")
    return scheduler


def _node_mapping_to_context(
    node_mapping: dict[str | Callable[[Path], str | None], str] | None = None,
    value_mapping: dict[Callable[[Path], Any], Any] | None = None,
):
    node_mapping = node_mapping or {}
    value_mapping = value_mapping or {}

    def _func(ui: MainWindow, step: WorkflowStep) -> dict[str, Any]:
        win = ui.window_for_id(step.id)
        if win is None:
            return {}
        val = win.value
        if not isinstance(val, _job_dir.JobDirectory):
            return {}
        # NOTE: the from_ file does NOT have to exist at this point.
        out = {}
        for from_, to_ in node_mapping.items():
            try:
                if isinstance(from_, str):
                    file_path = val.path.joinpath(from_)
                elif callable(from_):
                    returned_value = from_(val.path)
                    if returned_value is None:
                        continue
                    file_path = Path(returned_value)
                else:
                    raise TypeError(f"Unsupported from_ type: {type(from_)}")
                file_path = val.make_relative_path(file_path)
                file_path_rel = file_path.as_posix()
                if "." in to_:  # dict valule
                    to_, subkey = to_.split(".", 1)
                    if to_ not in out:
                        out[to_] = {}
                    out[to_][subkey] = file_path_rel
                else:
                    out[to_] = file_path_rel
            except Exception as e:
                _LOGGER.error("Error in node mapping from %r to %r: %s", from_, to_, e)
        for from_, to_ in value_mapping.items():
            try:
                if callable(from_):
                    returned_value = from_(val.path)
                    if returned_value is None:
                        continue
                else:
                    raise TypeError(f"Unsupported from_ type: {type(from_)}")
            except Exception as e:
                _LOGGER.error("Error in value mapping from %r to %r: %s", from_, to_, e)
                continue
            out[to_] = returned_value
        return out

    return _func


def plot_connected_jobs(tomo: bool = True):
    import matplotlib.pyplot as plt
    from himena_relion.relion5_tomo._builtins import _Relion5TomoJob

    xticklabels = []
    yticklabels = []
    for pre, post in CONNECTED_JOBS:
        if not (issubclass(pre, _Relion5TomoJob) or issubclass(post, _Relion5TomoJob)):
            if tomo:
                continue
        if post.__name__ not in xticklabels:
            xticklabels.append(post.__name__)
        if pre.__name__ not in yticklabels:
            yticklabels.append(pre.__name__)
    heatmap = np.zeros((len(yticklabels), len(xticklabels)), dtype=int)
    for pre, post in CONNECTED_JOBS:
        try:
            x = xticklabels.index(post.__name__)
            y = yticklabels.index(pre.__name__)
        except ValueError:
            continue
        heatmap[y, x] += 1
    plt.figure(figsize=(8, 8))
    for i in range(0, heatmap.shape[0], 5):
        plt.axhline(i - 0.5, color="gray", linewidth=0.5)
    for j in range(0, heatmap.shape[1], 5):
        plt.axvline(j - 0.5, color="gray", linewidth=0.5)
    plt.imshow(heatmap, cmap="Blues", interpolation="nearest")
    plt.xticks(ticks=np.arange(len(xticklabels)), labels=xticklabels, rotation=90)
    plt.yticks(ticks=np.arange(len(yticklabels)), labels=yticklabels)
    plt.xlabel("post")
    plt.ylabel("pre")
    plt.title("Connected RELION Jobs")
    plt.tight_layout()
    plt.show()
