from pathlib import Path

import watchfiles
from watchfiles import Change

__all__ = ["watch", "Change"]


def watch(path, recursive: bool = True):
    return watchfiles.watch(
        path,
        step=160,
        rust_timeout=400,
        yield_on_timeout=True,
        force_polling=Path(path).drive.startswith(r"\\wsl"),
        poll_delay_ms=300,
        recursive=recursive,
    )
