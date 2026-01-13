from typing import Annotated, Union


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
RESCALE = Annotated[
    int | None,
    {
        "label": "Rescaled box size (pix)",
        "tooltip": (
            "If given, particles will be re-scaled to this pixel size (must be an even "
            "number). Note that the particle diameter below will be in the down-scaled "
            "images."
        ),
        "group": "Extract",
    },
]
DO_INVERT = Annotated[
    bool,
    {
        "label": "Invert contrast",
        "tooltip": "If enabled, the contrast in the particles will be inverted.",
        "group": "Extract",
    },
]
DO_NORM = Annotated[
    bool,
    {
        "label": "Normalize particles",
        "tooltip": (
            "If enabled, particles will be normalized in the way RELION prefers it."
        ),
        "group": "Extract",
    },
]
DIAMETER = Annotated[
    float | None,
    {
        "label": "Diameter of background circle (pix)",
        "tooltip": (
            "Particles will be normalized to a mean value of zero and a "
            "standard-deviation of one for all pixels in the background area. The "
            "background area is defined as all pixels outside a circle with this given "
            "diameter in pixels (before rescaling). By default, 75% of the Particle "
            "box size will be used."
        ),
        "min": 0,
        "group": "Extract",
    },
]
WIGHT_DUST = Annotated[
    float | None,
    {
        "label": "Stddev for white dust removal",
        "tooltip": (
            "Remove very white pixels from the extracted particles if given. Pixels "
            "values higher than this many times the image standard deviation will be "
            "replaced with values from a Gaussian distribution."
        ),
        "min": 0,
        "group": "Extract",
    },
]
BLACK_DUST = Annotated[
    float | None,
    {
        "label": "Stddev for black dust removal",
        "tooltip": (
            "Remove very black pixels from the extracted particles if given. Pixels "
            "values higher than this many times the image standard deviation will be "
            "replaced with values from a Gaussian distribution."
        ),
        "min": 0,
        "group": "Extract",
    },
]

DO_RESET_OFFSET = Annotated[
    bool,
    {
        "label": "Reset refined offsets to zero",
        "tooltip": (
            "If enabled, the input origin offsets will be reset to zero. This may "
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
            "If enabled, the input coordinates will be re-centered according to the "
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
    Union[float, None],
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
            "Normally it should be enabled and bimodal angular priors will be "
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


BINNING = Annotated[
    int,
    {
        "label": "Binning factor",
        "min": 1,
        "tooltip": (
            "The tilt series images will be binned by this (real-valued) factor and "
            "then reconstructed in the specified box size above. Note that thereby the "
            "reconstructed region becomes larger when specifying binning factors "
            "larger than one."
        ),
        "group": "Reconstruct",
    },
]
BOX_SIZE = Annotated[
    int,
    {
        "label": "Box size (binned pix)",
        "tooltip": (
            "The initial box size of the reconstruction. A sufficiently large box size "
            "allows more of the high-frequency signal to be captured that has been "
            "delocalised by the CTF."
        ),
        "group": "Reconstruct",
    },
]
CROP_SIZE = Annotated[
    int | None,
    {
        "label": "Crop size (binned pix)",
        "tooltip": (
            "If set to a positive value, after construction, the resulting pseudo "
            "subtomograms are cropped to this size. A smaller box size allows the "
            "(generally expensive) refinement using relion_refine to proceed more "
            "rapidly."
        ),
        "group": "Reconstruct",
    },
]
MAX_DOSE = Annotated[
    float | None,
    {
        "label": "Maximum dose (e/A^2)",
        "tooltip": (
            "Tilt series frames with a dose higher than this maximum dose (in "
            "electrons per squared Angstroms) will not be included in the 3D "
            "pseudo-subtomogram, or in the 2D stack. For the latter, this will disc "
            "I/O operations and increase speed."
        ),
        "group": "Reconstruct",
    },
]
MIN_FRAMES = Annotated[
    int,
    {
        "label": "Minimum number of frames",
        "min": 1,
        "tooltip": (
            "Each selected pseudo-subtomogram need to be visible in at least this "
            "number of tilt series frames with doses below the maximum dose"
        ),
        "group": "Reconstruct",
    },
]
DO_STACK2D = Annotated[
    bool,
    {
        "label": "Extract as 2D stacks",
        "tooltip": (
            "If set to Yes, this program will write output subtomograms as 2D "
            "substacks. This is new as of relion-4.1, and the preferred way of "
            "generating subtomograms. If set to No, then relion-4.0 3D "
            "pseudo-subtomograms will be written out. Either can be used in subsequent "
            "refinements and classifications."
        ),
        "group": "Reconstruct",
    },
]
