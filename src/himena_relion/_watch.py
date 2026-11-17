import os
from pathlib import Path
from typing import Iterator

import watchfiles
from watchfiles import Change
from himena_relion._wsl import is_wsl_path

__all__ = ["watch", "watch_file", "Change"]


def watch(path, recursive: bool = True):
    return watchfiles.watch(
        path,
        step=160,
        rust_timeout=400,
        yield_on_timeout=True,
        force_polling=is_wsl_path(path),
        poll_delay_ms=300,
        recursive=recursive,
    )


def watch_file(path) -> Iterator[set[tuple[Change, str]]]:
    """Watch a single file, which may be replaced by another file.

    The parent directory is watched instead of the file itself. Files such as
    default_pipeline.star are replaced atomically (temporary file + `os.replace`), and
    on Linux, inotify watches the inode of the file, so a watch of the file itself
    receives no events after the first replacement.

    Changes of the other files in the directory are discarded. An empty set is yielded
    on timeout, or when only the other files changed.
    """
    path = Path(path)
    name = os.path.normcase(path.name)
    for changes in watch(path.parent, recursive=False):
        yield {
            (change, fp)
            for change, fp in changes
            if os.path.normcase(Path(fp).name) == name
        }
