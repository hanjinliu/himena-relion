from __future__ import annotations

import os
import json
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import subprocess
import logging
import time
from watchfiles import watch, Change
from himena_relion._utils import normalize_job_id, wait_for_file
from himena_relion._configs import get_relion_pipeliner_exe
from himena_relion import _job_dir

from himena_relion._pipeline import (
    NodeStatus,
    RelionDefaultPipeline,
    RelionJobInfo,
    is_all_inputs_ready,
)

_LOGGER = logging.getLogger(__name__)
_WATCHER_FILE_NAME = ".himena_pipeline_watcher.lock"


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
            pipeline = RelionDefaultPipeline.from_pipeline_star(path)
            self._on_job_state_changed(pipeline)
            for changes in watch(path, rust_timeout=400, yield_on_timeout=True):
                if not self._lock_file_path().exists():
                    break
                for change, fp in changes:
                    if change == Change.deleted:
                        continue
                    try:
                        pipeline = RelionDefaultPipeline.from_pipeline_star(path)
                    except Exception as e:
                        _LOGGER.warning(
                            "Failed to parse pipeline file: %s", e, exc_info=True
                        )
                    else:
                        # Update the internal data (thus, the flow chart)
                        self._on_job_state_changed(pipeline)

    def _on_job_state_changed(self, pipeline: RelionDefaultPipeline):
        self._state_to_job_map.clear()
        for job in pipeline.iter_nodes():
            _dict = self._state_to_job_map[job.status]
            _dict[job.path.as_posix()] = job

        if len(self._state_to_job_map[NodeStatus.SCHEDULED]) == 0:
            # No more jobs to run. Stop watching and remove the lock file.
            _LOGGER.info("No more jobs to run, exiting")
            return self._remove_lock()

        updated = False
        for job in self._state_to_job_map[NodeStatus.SCHEDULED].values():
            # run all the scheduled jobs whose dependencies are met
            if is_all_inputs_ready(job.path):
                _LOGGER.info("Job %s is ready to run, executing", job.path)
                execute_job(
                    job.path.as_posix(),
                    cwd=pipeline.project_dir,
                )
                updated = True
                path = self._relion_project_dir / job.path / "default_pipeline.star"
                if wait_for_file(path, num_retry=10, delay=0.05):
                    # This is required to trigger the on_job_updated callback in some
                    # widgets (such as QJobStateLabel).
                    path.touch()
        if updated:
            path = self._relion_project_dir / "default_pipeline.star"
            if path.exists():
                path.touch()
        elif len(self._state_to_job_map[NodeStatus.RUNNING]) == 0:
            # All the scheduled jobs cannot be run until the user fixes the dependencies,
            # overwrites the failed jobs, or adds new jobs. Stop watching.
            _LOGGER.info(
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
            raise WatcherAlreadyRunningError(
                f"Failed to acquire lock after {num_retry} retries. Another watcher "
                "might be running."
            )
        lock_info = {
            "pid": os.getpid(),
            "user": _get_user(),
        }
        path.write_text(json.dumps(lock_info, indent=2))
        try:
            yield
        finally:
            path.unlink(missing_ok=True)

    def _remove_lock(self):
        self._lock_file_path().unlink(missing_ok=True)


def _get_user() -> str:
    try:
        return os.getlogin()
    except OSError:
        # os.getlogin() may fail in some environments. In that case, fall back to the
        # default value.
        return "unknown"


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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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
        _LOGGER.warning("Error executing RELION job %s", job_name, exc_info=True)
        return None
    args = [get_relion_pipeliner_exe(), "--RunJobs", job_name]
    # NOTE: Because himena also uses Qt, RELION jobs that depend on napari (such as
    # ExcludeTiltSeries) may fail to start, saying no Qt bindings are available. This
    # seems to be due to environment variable QT_API being set to incompatible value
    # like "pyqt6".
    env = os.environ.copy()
    env.pop("QT_API", None)
    proc = subprocess.Popen(args, start_new_session=True, env=env, cwd=cwd)
    _LOGGER.info("Started RELION job %s with PID %d", job_name, proc.pid)
    execute_job._proc = proc  # retain the process object to prevent it from gc
    return RelionJobExecution(proc, job_dir)
