import gc
import sys
import warnings

import psutil
from himena_relion import _proc


def test_popen_detached_no_resource_warning():
    """Processes not waited for must not warn "subprocess xxx is still running"."""
    sleep = [sys.executable, "-c", "import time; time.sleep(60)"]
    with warnings.catch_warnings():
        warnings.simplefilter("error", ResourceWarning)
        short = _proc.popen_detached([sys.executable, "-c", "pass"])
        long = _proc.popen_detached(sleep)
        try:
            # wait for the exit without updating `returncode` of the Popen object
            psutil.wait_procs([psutil.Process(short.pid)], timeout=30)
        except psutil.NoSuchProcess:
            pass
        del short
        gc.collect()  # still retained
        # the next call reaps the exited process, and keeps the running one
        last = _proc.popen_detached([sys.executable, "-c", "pass"])
        gc.collect()
        assert [p.pid for p in _proc._DETACHED_PROCESSES] == [long.pid, last.pid]
        long.kill()
        long.wait()
        last.wait()
        _proc.popen_detached([sys.executable, "-c", "pass"]).wait()
        assert len(_proc._DETACHED_PROCESSES) == 1
