from __future__ import annotations

import os
import json
from collections import defaultdict
from contextlib import contextmanager
import datetime
from dataclasses import dataclass
from pathlib import Path
import subprocess
import time
import warnings
from watchfiles import watch, Change
from himena_relion._utils import (
    RelionPipelineLockError,
    normalize_job_id,
    update_default_pipeline,
    open_with_lock,
)
from himena_relion._configs import get_relion_pipeliner_exe
from himena_relion import _job_dir

from himena_relion._pipeline import (
    NodeStatus,
    RelionDefaultPipeline,
    RelionJobInfo,
    is_all_inputs_ready,
    ReadyState,
)
from himena_relion.consts import FileNames

_WATCHER_FILE_NAME = ".himena_pipeline_watcher.lock"
_WATCHER_LOG_FILE_NAME = ".himena_pipeline_watcher.log"


class RelionPipelineWatcher:
    def __init__(self, relion_dir: str | Path):
        super().__init__()
        self._relion_project_dir = Path(relion_dir).resolve()
        self._state_to_job_map = defaultdict[NodeStatus, dict[str, RelionJobInfo]](dict)

    def run(self):
        """Watch the job directory for changes."""
        path = self._relion_project_dir / "default_pipeline.star"
        if not path.exists():
            raise FileNotFoundError(f"Pipeline file not found at {path}")
        with self._acquire_lock():
            _clear_log()
            _print_log("Start pipeline watcher")
            pipeline = RelionDefaultPipeline.from_pipeline_star(path)
            self._on_job_state_changed(pipeline)
            _timeout_count = 0
            for changes in watch(path, rust_timeout=400, yield_on_timeout=True):
                if not self._lock_file_path().exists():
                    _print_log("Lock file removed, exiting")
                    break
                has_changes = any(ch != Change.deleted for ch, _ in changes)
                if not has_changes:
                    _timeout_count += 1
                    if _timeout_count > 25:
                        _timeout_count = 0
                        has_changes = True
                else:
                    _print_log("Job state change detected.")
                    _timeout_count = 0

                if has_changes:
                    try:
                        pipeline = RelionDefaultPipeline.from_pipeline_star(path)
                    except Exception as e:
                        _print_log(f"Failed to parse pipeline file: {e}")
                    else:
                        # Update the internal data (thus, the flow chart)
                        self._on_job_state_changed(pipeline)
        _print_log("End pipeline watcher")

    def _on_job_state_changed(self, pipeline: RelionDefaultPipeline):
        self._state_to_job_map.clear()
        for job in pipeline.iter_nodes():
            _dict = self._state_to_job_map[job.status]
            _dict[job.path.as_posix()] = job

        if len(self._state_to_job_map[NodeStatus.SCHEDULED]) == 0:
            # No more jobs to run. Stop watching and remove the lock file.
            _print_log("No more jobs to run, exiting")
            return self._remove_lock()

        updated = False
        files_to_touch: list[Path] = []
        default_pipeline_path = self._relion_project_dir / "default_pipeline.star"
        job_dir_path = self._relion_project_dir / job.path
        for job in self._state_to_job_map[NodeStatus.SCHEDULED].values():
            # run all the scheduled jobs whose dependencies are met
            match is_all_inputs_ready(job.path):
                case ReadyState.READY:
                    if filename := _job_state_file(job_dir_path):
                        _print_log(
                            f"Job {job.path} is scheduled and ready to run but "
                            f"contains {filename}. Skip."
                        )
                    else:
                        _print_log(f"Job {job.path} is ready to run, executing.")
                        execute_job(
                            job.path.as_posix(),
                            cwd=pipeline.project_dir,
                        )
                        updated = True
                        files_to_touch.append(job_dir_path / "default_pipeline.star")
                case ReadyState.FILE_NOT_FOUND:
                    _print_log(f"Job {job.path} cannot run because of missing inputs.")
                    job_dir_path.joinpath("run.err").write_text(
                        "himena-relion: Cannot run this job because some input files "
                        "are not found even though parent jobs are finished."
                    )
                    job_dir_path.joinpath(FileNames.EXIT_FAILURE).touch()
                    try:
                        with open_with_lock(default_pipeline_path) as f:
                            update_default_pipeline(
                                f, normalize_job_id(job.path), "Failed"
                            )
                    except RelionPipelineLockError:
                        _print_log(
                            "Failed to update default_pipeline.star to mark job "
                            f"{job.path} as Failed because `.relion_lock` exists."
                        )
                    else:
                        updated = True

        if updated:
            time.sleep(0.5)
            files_to_touch.append(default_pipeline_path)
            for fp in files_to_touch:
                if fp.exists():
                    fp.touch()

        elif len(self._state_to_job_map[NodeStatus.RUNNING]) == 0:
            # All the scheduled jobs cannot be run until the user fixes the dependencies,
            # overwrites the failed jobs, or adds new jobs. Stop watching.
            _print_log(
                "None of the scheduled jobs can be automatically started, exiting"
            )
            return self._remove_lock()

    def _lock_file_path(self) -> Path:
        return self._relion_project_dir / _WATCHER_FILE_NAME

    @contextmanager
    def _acquire_lock(self):
        path = self._lock_file_path()
        num_retry = 10
        for _ in range(num_retry):
            if not path.exists():
                break
            time.sleep(0.1)
        else:
            try:
                pid = read_pid_from_lock(path)
            except Exception:
                warnings.warn(
                    f"Pipeline watcher lock file {_WATCHER_FILE_NAME} seems broken. "
                    "This lock will be removed.",
                    RuntimeWarning,
                    stacklevel=1,
                )
                path.unlink()
            else:
                raise WatcherAlreadyRunningError(
                    f"Failed to acquire lock after {num_retry} retries. Another "
                    f"watcher at PID {pid} is running."
                )
        lock_info = {
            "pid": os.getpid(),
            "user": get_user(),
        }
        path.write_text(json.dumps(lock_info, indent=2))
        try:
            yield
        finally:
            path.unlink(missing_ok=True)

    def _remove_lock(self):
        self._lock_file_path().unlink(missing_ok=True)


def get_user() -> str:
    """Get the username of the current user."""
    try:
        return os.getlogin()
    except OSError:
        # os.getlogin() may fail in some environments. In that case, fall back to the
        # default value.
        return "unknown"


def read_pid_from_lock(lock_path: Path) -> int:
    """Get the PID of the current watcher process"""
    js = json.loads(lock_path.read_text())
    return js["pid"]


class WatcherAlreadyRunningError(RuntimeError):
    """Raised when the process failed to acquire a lock."""


def run_watcher(relion_dir: str | Path, locked_ok: bool = True):
    watcher = RelionPipelineWatcher(relion_dir=relion_dir)
    try:
        watcher.run()
    except WatcherAlreadyRunningError:
        if locked_ok:
            # Another watcher is already running. Exiting.
            pass
        else:
            raise


def run_watcher_new_process(relion_dir: str | Path, locked_ok: bool = True):
    cmd = ["himena-relion", "watch", str(relion_dir)]
    if locked_ok:
        cmd.append("--lock-ok")
    # retain the process object.
    run_watcher_new_process._proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )


@dataclass
class RelionJobExecution:
    process: subprocess.Popen
    job_directory: _job_dir.JobDirectory


def execute_job(
    job_name: str | Path,
    ignore_error: bool = False,
    *,
    cwd=None,
) -> RelionJobExecution:
    """Execute a RELION job named `job_name` (such as "Class3D/job012/")."""
    job_name = normalize_job_id(job_name)
    try:
        job_dir = _job_dir.JobDirectory(Path(job_name).resolve())
    except FileNotFoundError as e:
        if not ignore_error:
            raise e
        _print_log(f"Error executing RELION job {job_name}: {e}")
        return None
    args = [get_relion_pipeliner_exe(), "--RunJobs", job_name]
    # NOTE: Because himena also uses Qt, RELION jobs that depend on napari (such as
    # ExcludeTiltSeries) may fail to start, saying no Qt bindings are available. This
    # seems to be due to environment variable QT_API being set to incompatible value
    # like "pyqt6".
    env = os.environ.copy()
    env.pop("QT_API", None)
    proc = subprocess.Popen(
        args,
        start_new_session=True,
        env=env,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _print_log(f"Started RELION job {job_name} with PID {proc.pid}")
    execute_job._proc = proc  # retain the process object to prevent it from gc
    return RelionJobExecution(proc, job_dir)


def _print_log(text: str):
    with open(_WATCHER_LOG_FILE_NAME, "a") as f:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] {text}", file=f)


def _clear_log():
    Path(_WATCHER_LOG_FILE_NAME).write_text("")


def _job_state_file(job: RelionJobInfo, job_dir_path: Path) -> str:
    for filename in [
        FileNames.EXIT_FAILURE,
        FileNames.EXIT_ABORTED,
        FileNames.EXIT_SUCCESS,
        FileNames.ABORT_NOW,
    ]:
        if (job_dir_path / filename).exists():
            return filename
    return None
