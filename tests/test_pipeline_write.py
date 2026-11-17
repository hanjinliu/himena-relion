"""default_pipeline.star must never be left empty or partially written.

The file used to be rewritten in place (truncate, then write), so an error or a kill
in between left an empty file, and readers saw it empty during every update.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest
from starfile_rs.schema import ValidationError

from himena_relion import _utils
from himena_relion._pipeline import RelionDefaultPipeline
from himena_relion.consts import DEFAULT_PIPELINE_BACKUP, DEFAULT_PIPELINE_STAR
from himena_relion.pipeline_watcher import _WATCHER_LOG_FILE_NAME, RelionPipelineWatcher
from himena_relion.schemas import RelionPipelineModel
from ._utils import DEFAULT_PIPELINES_DIR

JOB = "CtfFind/job003/"  # "Scheduled" in full.star


@pytest.fixture
def pipeline_path(tmp_path: Path) -> Path:
    path = tmp_path / DEFAULT_PIPELINE_STAR
    shutil.copyfile(DEFAULT_PIPELINES_DIR / "full.star", path)
    return path


def _tmp_files(directory: Path) -> list[Path]:
    return list(directory.glob("*.tmp"))


def test_write_bytes_atomic(tmp_path: Path):
    path = tmp_path / "a.star"
    path.write_bytes(b"old\n")
    _utils.write_bytes_atomic(path, b"new\r\nline\n")
    assert path.read_bytes() == b"new\r\nline\n"
    _utils.write_bytes_atomic(tmp_path / "b.star", b"created\n")
    assert tmp_path.joinpath("b.star").read_bytes() == b"created\n"
    assert _tmp_files(tmp_path) == []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
def test_write_bytes_atomic_keeps_permissions(tmp_path: Path):
    path = tmp_path / "a.star"
    path.write_bytes(b"old\n")
    path.chmod(0o664)
    _utils.write_bytes_atomic(path, b"new\n")
    assert path.stat().st_mode & 0o777 == 0o664


def test_write_bytes_atomic_falls_back_to_in_place(tmp_path: Path, monkeypatch):
    # On Windows, os.replace fails while another process has the file open.
    def _replace(src, dst):
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(_utils.os, "replace", _replace)
    path = tmp_path / "a.star"
    path.write_bytes(b"old content that is longer\n")
    _utils.write_bytes_atomic(path, b"new\n", replace_timeout=0.05)
    assert path.read_bytes() == b"new\n"
    assert _tmp_files(tmp_path) == []


def test_failed_update_leaves_file_unchanged(pipeline_path: Path, monkeypatch):
    original = pipeline_path.read_bytes()

    def _fail(self):
        raise RuntimeError("failed to serialize")

    monkeypatch.setattr(RelionPipelineModel, "to_string", _fail)
    with _utils.open_with_lock(pipeline_path) as f:
        _utils.update_default_pipeline(f, JOB, state="Running")  # only logged
    assert pipeline_path.read_bytes() == original


def test_write_error_is_raised(pipeline_path: Path, monkeypatch):
    original = pipeline_path.read_bytes()

    def _fail(path, data):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(_utils, "_write_temp_file", _fail)
    with pytest.raises(OSError, match="No space left"):
        with _utils.open_with_lock(pipeline_path) as f:
            _utils.update_default_pipeline(f, JOB, state="Running")
    assert pipeline_path.read_bytes() == original
    assert not pipeline_path.parent.joinpath(".relion_lock").exists()


def test_non_ascii_alias(pipeline_path: Path):
    # The file used to be written in the locale encoding (cp932 on Japanese Windows),
    # which cannot encode "é", and the error emptied the file.
    with _utils.open_with_lock(pipeline_path) as f:
        _utils.update_default_pipeline(f, JOB, alias="CtfFind/caf\xe9/")
    data = pipeline_path.read_bytes()
    assert "CtfFind/caf\xe9/".encode() in data
    assert b"\r\n" not in data


def test_file_is_not_modified_until_replaced(pipeline_path: Path, monkeypatch):
    original = pipeline_path.read_bytes()
    seen = []
    orig_to_string = RelionPipelineModel.to_string

    def _spy(self):
        seen.append(pipeline_path.read_bytes() == original)
        return orig_to_string(self)

    monkeypatch.setattr(RelionPipelineModel, "to_string", _spy)
    with _utils.open_with_lock(pipeline_path) as f:
        _utils.update_default_pipeline(f, JOB, state="Running")
    assert seen == [True]
    assert b"Running" in pipeline_path.read_bytes()


def test_concurrent_reader_never_sees_empty_file(pipeline_path: Path):
    stop = threading.Event()
    num_empty = 0
    num_reads = 0

    def _read():
        nonlocal num_empty, num_reads
        while not stop.is_set():
            try:
                data = pipeline_path.read_bytes()
            except PermissionError:
                continue  # Windows: the file is being replaced
            num_reads += 1
            if len(data) == 0:
                num_empty += 1

    thread = threading.Thread(target=_read, daemon=True)
    thread.start()
    try:
        for i in range(30):
            with _utils.open_with_lock(pipeline_path) as f:
                state = "Running" if i % 2 == 0 else "Scheduled"
                _utils.update_default_pipeline(f, JOB, state=state)
    finally:
        stop.set()
        thread.join()
    assert num_reads > 0
    assert num_empty == 0


def test_backup(pipeline_path: Path):
    original = pipeline_path.read_bytes()
    backup = pipeline_path.with_name(DEFAULT_PIPELINE_BACKUP)
    with _utils.open_with_lock(pipeline_path) as f:
        _utils.update_default_pipeline(f, JOB, state="Running")
    assert backup.read_bytes() == original

    # a broken file must not overwrite the last good backup
    pipeline_path.write_bytes(b"")
    with _utils.open_with_lock(pipeline_path) as f:
        f.write(original.decode())
    assert backup.read_bytes() == original


_SLOW_WRITER = textwrap.dedent(
    """
    import sys, time
    from himena_relion import _utils
    from himena_relion.schemas import RelionPipelineModel

    orig = RelionPipelineModel.to_string

    def slow(self):
        print("serializing", flush=True)
        time.sleep(60)
        return orig(self)

    RelionPipelineModel.to_string = slow
    with _utils.open_with_lock(sys.argv[1]) as f:
        _utils.update_default_pipeline(f, sys.argv[2], state="Running")
    """
)


def test_killed_writer_leaves_file_unchanged(pipeline_path: Path, tmp_path: Path):
    # e.g. `stop_outdated_watcher` terminates a watcher
    original = pipeline_path.read_bytes()
    script = tmp_path / "slow_writer.py"
    script.write_text(_SLOW_WRITER)
    proc = subprocess.Popen(
        [sys.executable, "-P", str(script), str(pipeline_path), JOB],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout.readline().strip() == "serializing"
    finally:
        proc.terminate()
        proc.wait(10)
        proc.stdout.close()
    assert pipeline_path.read_bytes() == original


def test_read_broken_pipeline(pipeline_path: Path):
    pipeline_path.write_bytes(b"")
    with pytest.raises(ValidationError):
        RelionDefaultPipeline.from_pipeline_star(
            pipeline_path, allow_empty=False, retry_delay=0.01
        )
    pipeline = RelionDefaultPipeline.from_pipeline_star(
        pipeline_path, retry_delay=0.01
    )
    assert len(pipeline) == 0

    # a project without any jobs is valid
    pipeline_path.write_text(
        "data_pipeline_general\n\n_rlnPipeLineJobCounter 1\n", newline="\n"
    )
    pipeline = RelionDefaultPipeline.from_pipeline_star(pipeline_path, allow_empty=False)
    assert len(pipeline) == 0


def test_read_pipeline_being_written(pipeline_path: Path):
    # RELION rewrites the file in place, so it may be empty for a moment.
    text = pipeline_path.read_bytes()
    pipeline_path.write_bytes(b"")

    def _write_later():
        time.sleep(0.15)
        pipeline_path.write_bytes(text)

    thread = threading.Thread(target=_write_later)
    thread.start()
    pipeline = RelionDefaultPipeline.from_pipeline_star(pipeline_path, allow_empty=False)
    thread.join()
    assert len(pipeline) == 3


def test_watcher_keeps_running_if_pipeline_is_broken(pipeline_path: Path, monkeypatch):
    project = pipeline_path.parent
    monkeypatch.chdir(project)  # the watcher log is written in the cwd
    watcher = RelionPipelineWatcher(project)
    lock = watcher._lock_file_path()
    lock.write_text("{}")
    pipeline_path.write_bytes(b"")
    watcher._check_pipeline(pipeline_path)
    # The empty file was once taken as "No more jobs to run", and the watcher exited.
    assert lock.exists()
    assert "Failed to parse pipeline file" in project.joinpath(
        _WATCHER_LOG_FILE_NAME
    ).read_text()
