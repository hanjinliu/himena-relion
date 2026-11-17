from __future__ import annotations

import queue
import threading
import time
from pathlib import Path

from himena_relion._utils import write_text_atomic
from himena_relion._watch import Change, watch_file


def test_watch_file_detects_atomic_replacement(tmp_path: Path):
    """Every replacement of the file must be detected, not only the first one.

    On Linux, inotify watches the inode of a file, so watching default_pipeline.star
    itself receives no events after it is replaced by `os.replace`.
    """
    path = tmp_path / "default_pipeline.star"
    other = tmp_path / "other.star"
    path.write_text("v0\n")
    detected: queue.Queue[tuple[Change, str]] = queue.Queue()
    ready = threading.Event()
    stop = threading.Event()

    def _run():
        for changes in watch_file(path):
            ready.set()  # the first yield is after the watcher started
            if stop.is_set():
                return
            for change, fp in changes:
                detected.put((change, Path(fp).name))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    try:
        assert ready.wait(10)
        for i in range(1, 4):
            write_text_atomic(other, f"other {i}\n")
            write_text_atomic(path, f"v{i}\n")
            deadline = time.monotonic() + 10
            names: list[str] = []
            while time.monotonic() < deadline:
                try:
                    change, name = detected.get(timeout=0.2)
                except queue.Empty:
                    continue
                names.append(name)
                if change != Change.deleted:
                    break
            else:
                raise AssertionError(f"Replacement {i} was not detected: {names}")
            assert set(names) == {path.name}
            time.sleep(0.5)  # wait for the rest of the events of this replacement
            while not detected.empty():
                assert detected.get()[1] == path.name
    finally:
        stop.set()
        thread.join(5)
