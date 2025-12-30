from typing import Annotated

EXCLUDETILT_CACHE_SIZE = Annotated[
    int,
    {
        "label": "Number of cached tilt series",
        "min": 1,
        "max": 10,
        "tooltip": "This controls the number of cached tilt series in Napari.",
        "group": "I/O",
    },
]
TOMO_THICKNESS = Annotated[
    float,
    {
        "label": "Estimated tomogram thickness (nm)",
        "min": 1.0,
        "tooltip": (
            "Estimated tomogram thickness (in nm) to be used for projection matching "
            "in AreTomo2 and for patch tracking in IMOD"
        ),
        "group": "I/O",
    },
]
