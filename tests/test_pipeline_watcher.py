"""Tests of the lock file of the pipeline watcher.

If a watcher is killed (e.g. together with the himena window), its lock file is left.
The lock must not prevent new watchers from starting, otherwise scheduled jobs are
never run.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil
import pytest
from himena import MainWindow

from himena_relion import pipeline_watcher
from himena_relion.pipeline_watcher import (
    _WATCHER_FILE_NAME,
    _WATCHER_LOG_FILE_NAME,
    RelionPipelineWatcher,
    WatcherAlreadyRunningError,
    is_lock_owner_alive,
)
from .test_hijack import _make_project


def _dead_pid() -> int:
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def _write_lock(path: Path, info: dict):
    path.write_text(json.dumps(info))


@pytest.fixture
def project(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # the watcher log is written in the cwd
    return tmp_path


def test_lock_owner_alive(project: Path):
    lock = project / _WATCHER_FILE_NAME
    _write_lock(lock, pipeline_watcher._lock_info())
    assert is_lock_owner_alive(lock)
    # old format of the lock file
    _write_lock(lock, {"pid": os.getpid(), "user": "me"})
    assert is_lock_owner_alive(lock)


def test_lock_owner_dead(project: Path):
    lock = project / _WATCHER_FILE_NAME
    # old format of the lock file, as left by a killed watcher
    _write_lock(lock, {"pid": _dead_pid(), "user": "me"})
    assert not is_lock_owner_alive(lock)
    info = pipeline_watcher._lock_info()
    info["pid"] = _dead_pid()
    _write_lock(lock, info)
    assert not is_lock_owner_alive(lock)


def test_lock_owner_pid_reused(project: Path):
    lock = project / _WATCHER_FILE_NAME
    # the watcher died an hour ago, and its PID is now used by this process
    info = pipeline_watcher._lock_info()
    info["create_time"] -= 3600
    _write_lock(lock, info)
    assert not is_lock_owner_alive(lock)


def test_lock_owner_of_other_machine(project: Path):
    lock = project / _WATCHER_FILE_NAME
    info = pipeline_watcher._lock_info()
    info["pid"] = _dead_pid()
    info["host"] = "another-host"
    _write_lock(lock, info)
    assert is_lock_owner_alive(lock)  # cannot be checked


def test_lock_broken(project: Path):
    lock = project / _WATCHER_FILE_NAME
    lock.write_text("{")
    with pytest.raises(ValueError):
        is_lock_owner_alive(lock)


def test_acquire_lock_removes_stale_lock(project: Path):
    lock = project / _WATCHER_FILE_NAME
    _write_lock(lock, {"pid": _dead_pid(), "user": "me"})
    watcher = RelionPipelineWatcher(project)
    with watcher._acquire_lock():
        info = json.loads(lock.read_text())
        assert info["pid"] == os.getpid()
        assert info["create_time"] == psutil.Process().create_time()
    assert not lock.exists()
    log = project.joinpath(_WATCHER_LOG_FILE_NAME).read_text()
    assert "Removed the lock of a watcher not running" in log


def test_acquire_lock_keeps_running_watcher(project: Path):
    lock = project / _WATCHER_FILE_NAME
    _write_lock(lock, pipeline_watcher._lock_info())
    watcher = RelionPipelineWatcher(project)
    with pytest.raises(WatcherAlreadyRunningError):
        with watcher._acquire_lock():
            pass
    assert lock.exists()


def test_watcher_runs_jobs_after_killed_watcher(project: Path, monkeypatch):
    job_dir = _make_project(project)
    old = time.time() - 60
    os.utime(job_dir.job_star(), (old, old))  # not a job that was just created
    _write_lock(project / _WATCHER_FILE_NAME, {"pid": _dead_pid(), "user": "me"})
    calls = []

    class _Proc:
        pid = 0

    monkeypatch.setattr(
        pipeline_watcher.subprocess,
        "Popen",
        lambda args, **_: calls.append(args) or _Proc(),
    )
    # the job stays scheduled because relion is not run. Stop after the first check.
    monkeypatch.setattr(pipeline_watcher, "watch", lambda path: iter([]))
    pipeline_watcher.run_watcher(project)
    assert len(calls) == 1
    assert "--RunJobs" in calls[0]
    assert not project.joinpath(_WATCHER_FILE_NAME).exists()


def test_watcher_process_is_detached(monkeypatch):
    popen_kwargs = []
    monkeypatch.setattr(
        pipeline_watcher.subprocess,
        "Popen",
        lambda args, **kwargs: popen_kwargs.append(kwargs),
    )
    pipeline_watcher.run_watcher_new_process("project")
    if sys.platform == "win32":
        flags = popen_kwargs[0]["creationflags"]
        assert flags & subprocess.CREATE_NO_WINDOW
        assert flags & subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        assert popen_kwargs[0]["start_new_session"]


def test_startup_removes_stale_lock(himena_ui: MainWindow, project: Path):
    from himena_relion.startup import on_himena_startup

    _make_project(project)
    lock = project / _WATCHER_FILE_NAME
    _write_lock(lock, {"pid": _dead_pid(), "user": "me"})
    on_himena_startup(himena_ui)
    assert not lock.exists()

    # a running watcher is kept
    _write_lock(lock, pipeline_watcher._lock_info())
    on_himena_startup(himena_ui)
    assert lock.exists()
