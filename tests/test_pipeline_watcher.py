"""Tests of the lock file of the pipeline watcher.

If a watcher is killed (e.g. together with the himena window), its lock file is left.
The lock must not prevent new watchers from starting, otherwise scheduled jobs are
never run.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import psutil
import pytest
from himena import MainWindow

from himena_relion import pipeline_watcher
from himena_relion.hijack import _base
from himena_relion.pipeline_watcher import (
    _WATCHER_FILE_NAME,
    _WATCHER_LOG_FILE_NAME,
    WATCHER_PROTOCOL,
    OutdatedWatcherError,
    RelionPipelineWatcher,
    WatcherAlreadyRunningError,
    is_lock_owner_alive,
    stop_outdated_watcher,
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
    _make_project(project)
    monkeypatch.setattr(_base, "_MARKER_GRACE_SEC", 0.0)  # do not wait for the marker
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
    popen_args = []
    popen_kwargs = []
    monkeypatch.setattr(
        pipeline_watcher.subprocess,
        "Popen",
        lambda args, **kwargs: popen_args.append(args) or popen_kwargs.append(kwargs),
    )
    pipeline_watcher.run_watcher_new_process("project")
    # `himena-relion` in PATH may be of another environment
    assert popen_args[0] == [
        sys.executable,
        "-P",
        "-m",
        "himena_relion",
        "watch",
        "project",
        "--lock-ok",
    ]
    if sys.platform == "win32":
        flags = popen_kwargs[0]["creationflags"]
        assert flags & subprocess.CREATE_NO_WINDOW
        assert flags & subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        assert popen_kwargs[0]["start_new_session"]


def test_run_watcher_as_module(tmp_path: Path):
    # `python -m himena_relion watch` must run the watcher
    proc = subprocess.run(
        [sys.executable, "-P", "-m", "himena_relion", "watch", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=120,
    )
    assert proc.returncode != 0
    assert "Pipeline file not found" in proc.stderr


### Watchers of older himena-relion ###


def _sleeping_process(*args: str) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)", *args]
    )


@pytest.fixture
def old_watcher(project: Path):
    """A running watcher of himena-relion before WATCHER_PROTOCOL was introduced."""
    proc = _sleeping_process("himena-relion", "watch", str(project), "--lock-ok")
    _write_lock(project / _WATCHER_FILE_NAME, {"pid": proc.pid, "user": "me"})
    yield proc
    if proc.poll() is None:
        proc.kill()
        proc.wait()


def test_lock_info_has_protocol():
    from himena_relion import __version__

    info = pipeline_watcher._lock_info()
    assert info["protocol"] == WATCHER_PROTOCOL
    assert info["version"] == __version__
    assert info["executable"] == sys.executable


def test_stop_outdated_watcher(project: Path, old_watcher: subprocess.Popen):
    assert stop_outdated_watcher(project)
    old_watcher.wait(timeout=10)
    assert not project.joinpath(_WATCHER_FILE_NAME).exists()
    log = project.joinpath(_WATCHER_LOG_FILE_NAME).read_text()
    assert "Stopped the pipeline watcher of an older himena-relion" in log


def test_up_to_date_watcher_is_not_stopped(project: Path):
    proc = _sleeping_process("himena-relion", "watch", str(project), "--lock-ok")
    try:
        info = pipeline_watcher._lock_info()
        info["pid"] = proc.pid
        info["create_time"] = psutil.Process(proc.pid).create_time()
        _write_lock(project / _WATCHER_FILE_NAME, info)
        assert not stop_outdated_watcher(project)
        assert proc.poll() is None
        assert project.joinpath(_WATCHER_FILE_NAME).exists()
    finally:
        proc.kill()
        proc.wait()


def test_old_lock_with_reused_pid(project: Path):
    # old lock files have no "create_time", and the PID is used by another process
    proc = _sleeping_process()
    try:
        _write_lock(project / _WATCHER_FILE_NAME, {"pid": proc.pid, "user": "me"})
        assert stop_outdated_watcher(project)
        assert proc.poll() is None  # not a watcher, must not be killed
        assert not project.joinpath(_WATCHER_FILE_NAME).exists()
    finally:
        proc.kill()
        proc.wait()


def test_outdated_watcher_of_other_machine(project: Path):
    lock = project / _WATCHER_FILE_NAME
    _write_lock(lock, {"pid": _dead_pid(), "user": "me", "host": "another-host"})
    with pytest.raises(OutdatedWatcherError, match="another machine"):
        stop_outdated_watcher(project)
    assert lock.exists()
    # new watchers cannot start
    with pytest.raises(WatcherAlreadyRunningError):
        with RelionPipelineWatcher(project)._acquire_lock():
            pass
    assert lock.exists()


def test_acquire_lock_replaces_outdated_watcher(
    project: Path, old_watcher: subprocess.Popen
):
    lock = project / _WATCHER_FILE_NAME
    watcher = RelionPipelineWatcher(project)
    with watcher._acquire_lock():
        old_watcher.wait(timeout=10)
        info = json.loads(lock.read_text())
        assert info["pid"] == os.getpid()
        assert info["protocol"] == WATCHER_PROTOCOL
    assert not lock.exists()


def test_startup_replaces_outdated_watcher(
    himena_ui: MainWindow, project: Path, old_watcher: subprocess.Popen, monkeypatch
):
    from himena_relion import startup

    _make_project(project)
    started = []
    monkeypatch.setattr(startup, "run_watcher_new_process", started.append)
    startup.on_himena_startup(himena_ui)
    old_watcher.wait(timeout=10)
    assert [Path(p).resolve() for p in started] == [project.resolve()]


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
