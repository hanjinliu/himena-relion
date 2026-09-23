import watchfiles
from watchfiles import Change
from himena_relion._wsl import is_wsl_path

__all__ = ["watch", "Change"]


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
