from typing import Annotated

MPI_TYPE = Annotated[
    int,
    {
        "label": "Number of MPI processes",
        "min": 1,
        "max": 64,
        "group": "Running",
    },
]
THREAD_TYPE = Annotated[
    int,
    {
        "label": "Number of threads",
        "min": 1,
        "max": 64,
        "group": "Running",
    },
]
DO_QUEUE_TYPE = Annotated[
    bool,
    {"label": "Submit to queue", "group": "Running"},
]
MIN_DEDICATED_TYPE = Annotated[
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
        "group": "Running",
    },
]
