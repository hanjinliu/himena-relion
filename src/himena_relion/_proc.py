from __future__ import annotations

import subprocess

# Processes that are started and left running. A `Popen` object emits a
# ResourceWarning "subprocess xxx is still running" if it is garbage-collected
# before the exit of the process is confirmed by `poll()` or `wait()`, even if the
# process has already exited.
_DETACHED_PROCESSES: list[subprocess.Popen] = []


def popen_detached(args, **kwargs) -> subprocess.Popen:
    """Start a process that is not waited for.

    The process object is retained until the process exits, so that it will not be
    garbage-collected while it is (or is considered to be) running.
    """
    # `poll()` reaps the processes that have exited.
    _DETACHED_PROCESSES[:] = [p for p in _DETACHED_PROCESSES if p.poll() is None]
    proc = subprocess.Popen(args, **kwargs)
    _DETACHED_PROCESSES.append(proc)
    return proc
