from typing import Annotated
import os


def _get_environ(value, default) -> int:
    val = os.environ.get(value, default)
    try:
        val = int(val)
    except ValueError:
        val = default
    return val


_MPI_MAX = _get_environ("RELION_MPI_MAX", 64)
_NR_THREADS_MAX = _get_environ("RELION_THREAD_MAX", 64)
_DO_QUEUE_DEFAULT = os.environ.get("RELION_QUEUE_USE", "0") in ("1", "Yes")
_MIN_DEDICATED_DEFAULT = _get_environ("RELION_MINIMUM_DEDICATED", 1)

NR_MPI = Annotated[
    int,
    {
        "label": "Number of MPI processes",
        "min": 1,
        "max": _MPI_MAX,
        "tooltip": (
            "Number of MPI nodes to use in parallel. When set to 1, MPI will not be "
            "used. The maximum can be set through the environment variable "
            "RELION_MPI_MAX."
        ),
        "group": "Running",
    },
]
NR_THREADS = Annotated[
    int,
    {
        "label": "Number of threads",
        "min": 1,
        "max": _NR_THREADS_MAX,
        "tooltip": (
            "Number of shared-memory (POSIX) threads to use in parallel. When set to "
            "1, no multi-threading will be used. The maximum can be set through the "
            "environment variable RELION_THREAD_MAX."
        ),
        "group": "Running",
    },
]
DO_QUEUE = Annotated[
    bool,
    {
        "label": "Submit to queue",
        "tooltip": (
            "If set to Yes, the job will be submit to a queue, otherwise the job will "
            "be executed locally. Note that only MPI jobs may be sent to a queue. The "
            "default can be set through the environment variable RELION_QUEUE_USE."
        ),
        "value": _DO_QUEUE_DEFAULT,
        "group": "Running",
    },
]
MIN_DEDICATED = Annotated[
    int,
    {
        "label": "Minimum dedicated cores per node",
        "min": 1,
        "max": 64,
        "tooltip": (
            "Minimum number of dedicated cores that need to be requested on each node. "
            "This is useful to force the queue to fill up entire nodes of a given "
            "size. The default can be set through the environment variable "
            "RELION_MINIMUM_DEDICATED."
        ),
        "value": _MIN_DEDICATED_DEFAULT,
        "group": "Running",
    },
]
