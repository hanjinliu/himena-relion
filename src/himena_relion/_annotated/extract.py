from typing import Annotated


SIZE = Annotated[
    int,
    {
        "label": "Particle box size (pix)",
        "tooltip": (
            "Size of the extracted particles (in pixels). This should be an even "
            "number!"
        ),
        "group": "Extract",
    },
]
DO_RESCALE = Annotated[
    int,
    {
        "label": "Rescaled box size (pix)",
        "tooltip": (
            "If set to Yes, particles will be re-scaled. Note that the particle "
            "diameter below will be in the down-scaled images."
        ),
        "group": "Extract",
    },
]
DO_INVERT = Annotated[
    bool,
    {
        "label": "Invert contrast",
        "tooltip": "If set to Yes, the contrast in the particles will be inverted.",
        "group": "Extract",
    },
]
DO_NORM = Annotated[
    bool,
    {
        "label": "Normalize particles",
        "tooltip": (
            "If set to Yes, particles will be normalized in the way RELION prefers it."
        ),
        "group": "Extract",
    },
]
DIAMETER = Annotated[
    float,
    {
        "label": "Diameter of background circle (pix)",
        "tooltip": (
            "Particles will be normalized to a mean value of zero and a "
            "standard-deviation of one for all pixels in the background area. The "
            "background area is defined as all pixels outside a circle with this given "
            "diameter in pixels (before rescaling). When specifying a negative value, "
            "a default value of 75% of the Particle box size will be used."
        ),
        "group": "Extract",
    },
]
WIGHT_DUST = Annotated[
    float,
    {
        "label": "Stddev for white dust removal",
        "tooltip": (
            "Remove very white pixels from the extracted particles. Pixels values "
            "higher than this many times the image stddev will be replaced with values "
            "from a Gaussian distribution.\n\nUse negative value to switch off dust "
            "removal."
        ),
        "group": "Extract",
    },
]
BLACK_DUST = Annotated[
    float,
    {
        "label": "Stddev for black dust removal",
        "tooltip": (
            "Remove very black pixels from the extracted particles. Pixels values "
            "higher than this many times the image stddev will be replaced with values "
            "from a Gaussian distribution.\n\nUse negative value to switch off dust "
            "removal."
        ),
        "group": "Extract",
    },
]

DO_RESET_OFFSET = Annotated[
    bool,
    {
        "label": "Reset refined offsets to zero",
        "tooltip": (
            "If set to Yes, the input origin offsets will be reset to zero. This may "
            "be useful after 2D classification of helical segments, where one does not "
            "want neighbouring segments to be translated on top of each other for a "
            "subsequent 3D refinement or classification."
        ),
        "group": "I/O",
    },
]
DO_RECENTER = Annotated[
    bool,
    {
        "label": "Recenter refined coordinates",
        "tooltip": (
            "If set to Yes, the input coordinates will be re-centered according to the "
            "refined origin offsets in the provided _data.star file. The unit is "
            "pixel, not angstrom. The origin is at the center of the box, not at the "
            "corner."
        ),
        "group": "I/O",
    },
]
RECENTER = Annotated[
    tuple[float, float, float],
    {
        "label": "Re-center on (X, Y, Z) coordinates (in pix)",
        "tooltip": (
            "Re-extract particles centered on this coordinate (in pixels in the "
            "reference)"
        ),
        "group": "I/O",
    },
]

MINIMUM_PICK_FOM = Annotated[
    float | None,
    {
        "label": "Minimum autopick FOM",
        "tooltip": (
            "The minimum value for the rlnAutopickFigureOfMerit for particles to be "
            "extracted."
        ),
        "group": "Extract",
    },
]
HELICAL_BIMODAL_ANGULAR_PRIORS = Annotated[
    bool,
    {
        "label": "Use bimodal angular priors",
        "tooltip": (
            "Normally it should be set to Yes and bimodal angular priors will be "
            "applied in the following classification and refinement jobs. Set to No if "
            "the 3D helix looks the same when rotated upside down."
        ),
        "group": "Helix",
    },
]
DO_EXTRACT_HELICAL_TUBES = Annotated[
    bool,
    {
        "label": "Coordinates are star-end only",
        "tooltip": (
            "Set to Yes if you want to extract helical segments from manually picked "
            "tube coordinates (starting and end points of helical tubes in RELION, "
            "EMAN or XIMDISP format). Set to No if segment coordinates (RELION "
            "auto-picked results or EMAN / XIMDISP segments) are provided."
        ),
        "group": "Helix",
    },
]
DO_CUT_INTO_SEGMENTS = Annotated[
    bool,
    {
        "label": "Cut helical tubes into segments",
        "tooltip": (
            "Set to Yes if you want to extract multiple helical segments with a fixed "
            "inter-box distance. If it is set to No, only one box at the center of "
            "each helical tube will be extracted."
        ),
        "group": "Helix",
    },
]
