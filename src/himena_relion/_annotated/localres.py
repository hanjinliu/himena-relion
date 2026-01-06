from typing import Annotated

ANGPIX = Annotated[float, {"label": "Pixel size (A)", "tooltip": (), "group": "I/O"}]
PVAL = Annotated[
    float,
    {
        "label": "P-value for significance",
        "tooltip": (
            "This value is typically left at 0.05. If you change it, report the "
            "modified value in your paper!"
        ),
        "group": "ResMap",
    },
]
MINRES = Annotated[
    float,
    {
        "label": "Highest resolution (A)",
        "tooltip": (
            "ResMaps minRes parameter. By default (0), the program will start at just "
            "above 2x the pixel size"
        ),
        "min": 0,
        "max": 100,
        "group": "ResMap",
    },
]
MAXRES = Annotated[
    float,
    {
        "label": "Lowest resolution (A)",
        "tooltip": (
            "ResMaps maxRes parameter. By default (0), the program will stop at 4x the "
            "pixel size"
        ),
        "min": 0,
        "max": 100,
        "group": "ResMap",
    },
]
STEPRES = Annotated[
    float,
    {
        "label": "Resolution step (A)",
        "tooltip": "ResMaps stepSize parameter.",
        "group": "ResMap",
    },
]
ADHOC_BFAC = Annotated[
    float,
    {
        "label": "User-provided B-factor (A^2)",
        "tooltip": (
            "Probably, the overall B-factor as was estimated in the postprocess is a "
            "useful value for here. Use negative values for sharpening. Be careful: if "
            "you over-sharpen your map, you may end up interpreting noise for signal!"
        ),
        "group": "RELION",
    },
]
FN_MTF = Annotated[
    str,
    {
        "label": "MTF of the detector",
        "tooltip": (
            "The MTF of the detector is used to complement the user-provided B-factor "
            "in the sharpening. If you don't have this curve, you can leave this field "
            "empty."
        ),
        "group": "RELION",
    },
]
