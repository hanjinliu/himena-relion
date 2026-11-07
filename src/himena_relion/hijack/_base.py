"""Base class and pipeline bookkeeping for "hijacked" RELION jobs.

A hijacked job is a standard RELION job (e.g. `relion.select.interactive`) that is run
by himena-relion's own implementation in the himena main window. The job directory,
job.star and input/output nodes in the pipeline are exactly the same as those created
by RELION (`relion_pipeliner --addJobFromStar`), so the project stays fully compatible
with the original RELION.

The flow of a hijacked job is:

1. When the job is created (or overwritten/continued) from himena-relion, the file
   `USE_HIMENA_IMPL` is written in the job directory, unless the "Use RELION GUI"
   parameter (`use_relion_gui`, not written in job.star) is checked.
2. When the job is ready to run, the pipeline watcher does not call
   `relion_pipeliner --RunJobs`. It only marks the job as "Running" (`start_job`).
3. The himena main window opens the running job, and its Results tab shows the widget
   provided by the hijacker class instead of the job results.
4. The widget writes the output files and marks the job as finished (`finish_job`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import datetime
import json
import logging
import shutil
import time
import tomllib
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any

from himena_relion._job_dir import JobDirectory
from himena_relion._utils import (
    RelionPipelineLockError,
    open_with_lock,
    update_default_pipeline,
)
from himena_relion.consts import (
    DEFAULT_PIPELINE_STAR,
    NO,
    NODES_DIR,
    YES,
    FileNames,
    RelionJobState,
)
from himena_relion.schemas import JobStarModel, RelionPipelineModel

if TYPE_CHECKING:
    from himena_relion._widgets import JobWidgetBase

_LOGGER = logging.getLogger(__name__)
_HIJACKERS: list[type[HijackedJob]] = []
_PIPELINE_CONTROL_FILES = [
    FileNames.ABORT_NOW,
    FileNames.EXIT_ABORTED,
    FileNames.EXIT_SUCCESS,
    FileNames.EXIT_FAILURE,
]
# Seconds to wait for USE_HIMENA_IMPL to be written after the job is added by
# relion_pipeliner (see `wait_for_marker`).
_MARKER_GRACE_SEC = 2.0
# Job parameter to run a job by RELION even if it can be hijacked. It is a parameter
# of the job widgets only and is not written in job.star; USE_HIMENA_IMPL is written
# only when it is false.
USE_RELION_GUI = "use_relion_gui"


class HijackedJob(ABC):
    """A standard RELION job run by himena-relion's own implementation.

    Subclasses must define `type_label` and `create_widget`. Output files written by
    the widget must be the same as those of the original RELION program, because the
    output nodes are already registered in the pipeline by RELION.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.__name__.startswith("_"):
            _HIJACKERS.append(cls)

    @classmethod
    @abstractmethod
    def type_label(cls) -> str:
        """RELION job type label of the job to hijack (e.g. relion.select.interactive)"""

    @classmethod
    def matches(cls, job_params: dict[str, str]) -> bool:
        """Return True if the job with these parameters should be hijacked.

        Override this method if only part of the jobs of the type are supported.
        """
        return True

    @classmethod
    def import_path(cls) -> str:
        """Import path of this class, written as `himena_class` in USE_HIMENA_IMPL."""
        return f"{cls.__module__}:{cls.__name__}"

    @classmethod
    @abstractmethod
    def create_widget(cls, job_dir: JobDirectory) -> JobWidgetBase:
        """Create the widget shown in the Results tab while the job is running.

        The widget is responsible for writing the outputs and calling `finish_job`.
        """


def iter_hijackers() -> list[type[HijackedJob]]:
    """Return all the registered hijacker classes."""
    _import_builtin_hijackers()
    return list(_HIJACKERS)


def find_hijacker(job_dir: JobDirectory) -> type[HijackedJob] | None:
    """Find the hijacker class that can run the job, from its job.star."""
    try:
        job_star = JobStarModel.validate_file(job_dir.job_star())
    except Exception:
        return None
    type_label = job_star.job.job_type_label
    params = job_star.joboptions_values.to_dict()
    for hijacker in iter_hijackers():
        if hijacker.type_label() == type_label and hijacker.matches(params):
            return hijacker
    return None


def pick_hijacker(import_path: str) -> type[HijackedJob] | None:
    """Import the hijacker class from the import path like `module:ClassName`."""
    if import_path.count(":") != 1:
        return None
    mod_name, cls_name = import_path.split(":")
    try:
        cls = getattr(import_module(mod_name), cls_name, None)
    except ImportError:
        return None
    if isinstance(cls, type) and issubclass(cls, HijackedJob):
        return cls
    return None


def _import_builtin_hijackers():
    from himena_relion.hijack import select_interactive  # noqa: F401


### USE_HIMENA_IMPL marker ###


def uses_himena_impl(job_dir: JobDirectory) -> bool:
    """True if the job is marked to be run by himena-relion."""
    return job_dir.path.joinpath(FileNames.USE_HIMENA_IMPL).exists()


def update_marker(
    job_dir: JobDirectory, use_relion_gui: bool = False
) -> type[HijackedJob] | None:
    """Write USE_HIMENA_IMPL if the job can be hijacked, otherwise remove it.

    This must be called before the job is scheduled, so that the pipeline watcher
    never runs the job with `relion_pipeliner`. If `use_relion_gui` is true, the
    marker is removed so that the job is run by RELION as usual.
    """
    marker = job_dir.path / FileNames.USE_HIMENA_IMPL
    if not use_relion_gui and (hijacker := find_hijacker(job_dir)):
        write_marker(job_dir, {"himena_class": hijacker.import_path()})
        return hijacker
    marker.unlink(missing_ok=True)
    return None


def has_hijacker(type_label: str) -> bool:
    """True if some jobs of this type can be run by himena-relion."""
    return any(h.type_label() == type_label for h in iter_hijackers())


def job_params_with_marker(job_dir: JobDirectory) -> dict[str, Any]:
    """Parameters of an existing job, for the job parameter widgets.

    These are the parameters in job.star, plus `use_relion_gui` for job types that
    can be hijacked. `use_relion_gui` is not written in job.star; it is "Yes" when the
    job has no USE_HIMENA_IMPL.
    """
    params: dict[str, Any] = job_dir.get_job_params_as_dict()
    if has_hijacker(job_dir.job_type_label()):
        params[USE_RELION_GUI] = NO if uses_himena_impl(job_dir) else YES
    return params


def write_marker(job_dir: JobDirectory, fields: dict[str, str]) -> Path:
    """Write USE_HIMENA_IMPL in TOML format.

    Fields:
    - himena_class: import path of the `HijackedJob` subclass ("module:ClassName").
    """
    lines = [
        "# This job is run by himena-relion instead of relion_pipeliner.",
        "# Delete this file to run the job by RELION.",
    ]
    for key, value in fields.items():
        if not isinstance(value, str):
            raise TypeError(f"Value of {key!r} must be a string, got {value!r}")
        # JSON strings are valid TOML basic strings
        lines.append(f"{key} = {json.dumps(value)}")
    marker = job_dir.path / FileNames.USE_HIMENA_IMPL
    tmp = marker.with_name(marker.name + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", newline="\n")
    tmp.replace(marker)  # the watcher must never see a partially written file
    return marker


def read_marker(job_dir: JobDirectory) -> dict[str, Any]:
    """Read the fields of USE_HIMENA_IMPL (empty if missing or invalid)."""
    marker = job_dir.path / FileNames.USE_HIMENA_IMPL
    try:
        return tomllib.loads(marker.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def marked_hijacker(job_dir: JobDirectory) -> type[HijackedJob] | None:
    """The hijacker class written in USE_HIMENA_IMPL, if any."""
    if not uses_himena_impl(job_dir):
        return None
    import_path = read_marker(job_dir).get("himena_class", "")
    if isinstance(import_path, str) and (hijacker := pick_hijacker(import_path)):
        return hijacker
    return find_hijacker(job_dir)


def running_hijacker(job_dir: JobDirectory) -> type[HijackedJob] | None:
    """The hijacker class if the job is running with himena-relion's implementation."""
    if not uses_himena_impl(job_dir):
        return None
    if job_dir.state() is not RelionJobState.RUNNING or job_dir.is_scheduled():
        return None
    return marked_hijacker(job_dir)


def wait_for_marker(job_dir: JobDirectory) -> bool:
    """Wait for USE_HIMENA_IMPL of a job that was just added to the pipeline.

    `relion_pipeliner --addJobFromStar` adds the job to the pipeline before the main
    window writes USE_HIMENA_IMPL. A pipeline watcher that is already running could
    find the job in this short period, so wait a moment for jobs that can be hijacked.
    """
    if uses_himena_impl(job_dir):
        return True
    if find_hijacker(job_dir) is None:
        return False
    try:
        age = time.time() - job_dir.job_star().stat().st_mtime
    except OSError:
        return False
    if age < _MARKER_GRACE_SEC:
        time.sleep(min(_MARKER_GRACE_SEC - age, _MARKER_GRACE_SEC))
    return uses_himena_impl(job_dir)


### Pipeline bookkeeping ###


def start_job(job_dir: JobDirectory) -> None:
    """Mark the job as running, without running any program.

    This does what `relion_pipeliner --RunJobs` does before running the command:
    remove the pipeline control files, set the job status to "Running" and write a
    note in note.txt.
    """
    for fname in _PIPELINE_CONTROL_FILES:
        job_dir.path.joinpath(fname).unlink(missing_ok=True)
    # The status must be updated synchronously, otherwise the pipeline watcher may
    # start this job again.
    set_job_status(job_dir, "Running")
    # RELION redirects the outputs by `>> run.out 2>> run.err`, which creates both
    # files (and keeps the contents of the previous runs).
    for fname in ["run.out", "run.err"]:
        job_dir.path.joinpath(fname).open("a").close()
    hijacker = marked_hijacker(job_dir)
    impl = hijacker.import_path() if hijacker else "himena-relion"
    _append_note(job_dir, f"(run in the himena-relion main window by {impl})")


def finish_job(job_dir: JobDirectory, status: str) -> None:
    """Mark the job as finished, like RELION does by `checkProcessCompletion`.

    Raises `RelionPipelineLockError` if the pipeline could not be updated.
    """
    match status:
        case "Succeeded":
            fname = FileNames.EXIT_SUCCESS
        case "Failed":
            fname = FileNames.EXIT_FAILURE
        case "Aborted":
            fname = FileNames.EXIT_ABORTED
        case _:
            raise ValueError(f"Invalid finished status: {status!r}")
    # The control file must exist before the status is updated, because the
    # pipeline watcher checks it to see whether the child jobs can start.
    job_dir.path.joinpath(fname).touch()
    try:
        set_job_status(job_dir, status)
    except RelionPipelineLockError:
        job_dir.path.joinpath(fname).unlink(missing_ok=True)
        raise
    for other in _PIPELINE_CONTROL_FILES:
        if other != fname:
            job_dir.path.joinpath(other).unlink(missing_ok=True)
    if status == "Succeeded":
        try:
            touch_output_node_files(job_dir)
        except Exception:
            _LOGGER.warning("Failed to update %s", NODES_DIR, exc_info=True)


def set_job_status(job_dir: JobDirectory, status: str, wait_sec: float = 5.0):
    """Update the job status in default_pipeline.star (and its copies)."""
    rln_dir = job_dir.relion_project_dir
    job_id = job_dir.job_normal_id()
    default_pipeline = rln_dir / DEFAULT_PIPELINE_STAR
    with open_with_lock(default_pipeline, wait_sec=wait_sec) as f:
        update_default_pipeline(f, job_id, state=status)
    if status == "Running":
        # RELION writes job_pipeline.star with the "Running" status, and copies the
        # default_pipeline.star to the job directory when a job starts.
        if (job_pipeline := job_dir.job_pipeline()).exists():
            with job_pipeline.open("r+", newline="") as f:
                update_default_pipeline(f, job_id, state=status)
        shutil.copyfile(default_pipeline, job_dir.path / DEFAULT_PIPELINE_STAR)


def append_run_out(job_dir: JobDirectory, msg: str):
    """Append a message to run.out, like the stdout of RELION programs."""
    with job_dir.path.joinpath("run.out").open("a", newline="\n") as f:
        f.write(msg.rstrip("\n") + "\n")


def append_run_err(job_dir: JobDirectory, msg: str):
    """Append a message to run.err, like the stderr of RELION programs."""
    with job_dir.path.joinpath("run.err").open("a", newline="\n") as f:
        f.write(msg.rstrip("\n") + "\n")


def _append_note(job_dir: JobDirectory, command: str):
    now = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y")
    with job_dir.path.joinpath("note.txt").open("a", newline="\n") as f:
        f.write(
            f"\n ++++ Executing new job on {now}\n"
            f" ++++ with the following command(s): \n{command}\n ++++ \n"
        )


def touch_output_node_files(job_dir: JobDirectory) -> list[Path]:
    """Touch the files in .Nodes/ for the outputs, as `touchTemporaryNodeFile`."""
    rln_dir = job_dir.relion_project_dir
    job_id = job_dir.job_normal_id()
    pipeline = RelionPipelineModel.validate_file(rln_dir / DEFAULT_PIPELINE_STAR)
    is_this = pipeline.processes.process_name == job_id
    alias = pipeline.processes.alias.filter(is_this)
    alias = alias[0] if len(alias) > 0 else "None"
    if pipeline.output_edges is None:
        return []
    outputs = set(
        pipeline.output_edges.to_node.filter(pipeline.output_edges.process == job_id)
    )
    depths = pipeline.nodes.type_label_depth
    if depths is None:
        depths = [1] * len(pipeline.nodes.name)
    touched: list[Path] = []
    for name, type_label, depth in zip(
        pipeline.nodes.name, pipeline.nodes.type_label, depths
    ):
        if name not in outputs or not rln_dir.joinpath(name).exists():
            continue
        if alias != "None":
            # e.g. Select/job010/particles.star -> Select/my_alias/particles.star
            node_path = alias.rstrip("/") + "/" + name[len(job_id) :]
        else:
            node_path = name
        labels = [type_label.split(".")[0]]
        if depth is not None and int(depth) > 1:
            labels.append(".".join(type_label.split(".")[: int(depth)]))
        for label in labels:
            path = rln_dir / NODES_DIR / label / node_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            touched.append(path)
    return touched
