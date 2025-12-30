from typing import Annotated

DONT_SKIP_ALIGN = Annotated[
    bool,
    {
        "label": "Perform image alignment",
        "tooltip": (
            "If set to No, then rather than performing both alignment and "
            "classification, only classification will be performed. This allows the "
            "use of very focused masks. This requires that the optimal orientations "
            "of all particles are already stored in the input STAR file."
        ),
        "group": "Sampling",
    },
]
SIGMA_TILT = Annotated[
    float,
    {
        "label": "Prior width on tilt angle",
        "tooltip": (
            "The width of the prior on the tilt angle: angular searches will be +/-3 "
            "times this value. Tilt priors will be defined when particles have been "
            "picked as filaments, on spheres or on manifolds. Setting this width to "
            "a negative value will lead to no prior being used on the tilt angle."
        ),
        "group": "Sampling",
    },
]
ALLOW_COARSER_SAMPLING = Annotated[
    bool,
    {
        "label": "Allow coarser sampling",
        "tooltip": (
            "If set to Yes, the program will use coarser angular and translational "
            "samplings if the estimated accuracies of the assignments is still low in "
            "the earlier iterations. This may speed up the calculations."
        ),
        "group": "Sampling",
    },
]
ANG_SAMPLING = Annotated[
    str,
    {
        "label": "Angular sampling interval",
        "choices": [
            "30 degrees",
            "15 degrees",
            "7.5 degrees",
            "3.7 degrees",
            "1.8 degrees",
            "0.9 degrees",
            "0.5 degrees",
            "0.2 degrees",
            "0.1 degrees",
        ],
        "tooltip": (
            "There are only a few discrete angular samplings possible because we use "
            "the HealPix library to generate the sampling of the first two Euler "
            "angles on the sphere. The samplings are approximate numbers and vary "
            "slightly over the sphere.\n\nIf auto-sampling is used, this will be the "
            "value for the first iteration(s) only, and the sampling rate will be "
            "increased automatically after that."
        ),
        "group": "Sampling",
    },
]
OFFSET_RANGE_STEP = Annotated[
    tuple[float, float],
    {
        "label": "Offset search range/step (pix)",
        "tooltip": (
            "Probabilities will be calculated only for translations in a circle with "
            "this radius (in pixels). The center of this circle changes at every "
            "iteration and is placed at the optimal translation for each image in "
            "the previous iteration.\n\nIf auto-sampling is used, this will be the "
            "value for the first iteration(s) only, and the sampling rate will be "
            "increased automatically after that."
        ),
        "group": "Sampling",
    },
]
RELAX_SYMMETRY = Annotated[
    str,
    {
        "label": "Relax symmetry",
        "tooltip": (
            "With this option, poses related to the standard local angular search "
            "range by the given point group will also be explored. For example, if "
            "you have a pseudo-symmetric dimer A-A', refinement or classification in "
            "C1 with symmetry relaxation by C2 might be able to improve distinction "
            "between A and A'. Note that the reference must be more-or-less aligned "
            "to the convention of (pseudo-)symmetry operators. For details, see Ilca "
            "et al 2019 and Abrishami et al 2020 cited in the About dialog."
        ),
        "group": "Sampling",
    },
]

LOC_ANG_SAMPLING = Annotated[
    str,
    {
        "label": "Local angular sampling interval",
        "choices": [
            "30 degrees",
            "15 degrees",
            "7.5 degrees",
            "3.7 degrees",
            "1.8 degrees",
            "0.9 degrees",
            "0.5 degrees",
            "0.2 degrees",
            "0.1 degrees",
        ],
        "tooltip": (
            "In the automated procedure to increase the angular samplings, local "
            "angular searches of -6/+6 times the sampling rate will be used from this "
            "angular sampling rate onwards. For most lower-symmetric particles a "
            "value of 1.8 degrees will be sufficient. Perhaps icosahedral symmetries "
            "may benefit from a smaller value such as 0.9 degrees."
        ),
        "group": "Sampling",
    },
]
