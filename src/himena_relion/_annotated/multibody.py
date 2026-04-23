from typing import Annotated
from himena.qt.magicgui import ToggleButtons
from himena_relion._widgets._magicgui import PathDrop

FN_IN = Annotated[
    str,
    {
        "label": "Consensus refinement optimiser.star",
        "tooltip": (
            "Select the *_optimiser.star file for the iteration of the consensus "
            "refinement from which you want to start multi-body refinement."
        ),
        "widget_type": PathDrop,
        "type_label": "OptimiserData",
        "allowed_extensions": [".star"],
        "group": "I/O",
    },
]

FN_BODIES = Annotated[
    str,
    {
        "label": "Body STAR file",
        "tooltip": (
            "Provide the STAR file with all information about the bodies to be used "
            "in multi-body refinement. An example for a three-body refinement would "
            "look like this: \n\n"
            "<code>data_"
            "loop_"
            "_rlnBodyMaskName"
            "_rlnBodyRotateRelativeTo"
            "_rlnBodySigmaAngles"
            "_rlnBodySigmaOffset"
            "large_body_mask.mrc 2 10 2"
            "small_body_mask.mrc 1 10 2"
            "head_body_mask.mrc 2 10 2</code>\n\n"
            "Where each data line represents a different body, and: "
            "<ul>"
            "<li>rlnBodyMaskName contains the name of a soft-edged mask with values in "
            "[0,1] that define the body;</li> "
            "<li>rlnBodyRotateRelativeTo defines relative to which other body this "
            "body rotates (first body is number 1);</li> "
            "<li>rlnBodySigmaAngles and _rlnBodySigmaOffset are the standard "
            "deviations (widths) of Gaussian priors on the consensus rotations and "
            "translations;</li> "
            "</ul>"
            "Optionally, there can be a fifth column with _rlnBodyReferenceName. Entries can be 'None' (without the ''s) or the name of a MRC map with an initial reference for that body. In case the entry is None, the reference will be taken from the density in the consensus refinement."
            "Also note that larger bodies should be above smaller bodies in the STAR file. For more information, see the multi-body paper."
        ),
        "widget_type": PathDrop,
        "allowed_extensions": [".star"],
        "group": "I/O",
    },
]

DO_SUBTRACTED_BODIES = Annotated[
    bool,
    {
        "label": "Particle used for reconstruction",
        "choices": [("Subtracted", True), ("Original", False)],
        "tooltip": (
            "If set to 'Subtracted', then the reconstruction of each of the bodies "
            "will use the subtracted images. This may give useful insights about how "
            "well the subtraction worked.\n"
            "If set to 'Original', the original particles are used for reconstruction "
            "(while the subtracted ones are still used for alignment). This will "
            "result in fuzzy densities for bodies outside the one used for refinement."
        ),
        "widget_type": ToggleButtons,
        "group": "I/O",
    },
]

SAMPING = Annotated[
    str,
    {
        "label": "Initial angular sampling",
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
            "the HealPix library to generate the sampling of the first two Euler angles "
            "on the sphere. The samplings are approximate numbers and vary slightly "
            "over the sphere.\n\nNote that this will only be the value for the first "
            "few iteration(s): the sampling rate will be increased automatically after "
            "that."
        ),
        "group": "Auto-sampling",
    },
]

OFFSET_RANGE = Annotated[
    int,
    {
        "label": "Initial offset range (pix)",
        "min": 0,
        "max": 100,
        "tooltip": (
            "Probabilities will be calculated only for translations in a circle with "
            "this radius (in pixels). The center of this circle changes at every "
            "iteration and is placed at the optimal translation for each image in the "
            "previous iteration.\n\nNote that this will only be the value for the "
            "first few iteration(s): the sampling rate will be increased automatically "
            "after that."
        ),
        "group": "Auto-sampling",
    },
]
OFFSET_STEP = Annotated[
    float,
    {
        "label": "Initial offset step (pix)",
        "min": 0.1,
        "max": 5.0,
        "tooltip": (
            "Translations will be sampled with this step-size (in pixels). "
            "Translational sampling is also done using the adaptive approach. "
            "Therefore, if adaptive=1, the translations will first be evaluated on a "
            "2x coarser grid.\n\nNote that this will only be the value for the first "
            "few iteration(s): the sampling rate will be increased automatically after "
            "that."
        ),
        "group": "Auto-sampling",
    },
]
DO_ANALYSE = Annotated[
    bool,
    {
        "label": "Run flexibility analysis",
        "tooltip": (
            "If set to Yes, after the multi-body refinement has completed, a PCA "
            "analysis will be run on the orientations all all bodies in the data set. "
            "This can be set to No initially, and then the job can be continued "
            "afterwards to only perform this analysis."
        ),
        "group": "Analyse",
    },
]
NR_MOVIES = Annotated[
    int,
    {
        "label": "Number of eigenvector movies",
        "min": 1,
        "max": 20,
        "tooltip": (
            "Series of ten output maps will be generated along this many eigenvectors. "
            "These maps can be opened as a 'Volume Series' in UCSF Chimera, and then "
            "displayed as a movie. They represent the principal motions in the "
            "particles."
        ),
        "group": "Analyse",
    },
]
DO_SELECT = Annotated[
    bool,
    {
        "label": "Select particles based on eigenvalues",
        "tooltip": (
            "If set to Yes, a particles.star file is written out with all particles "
            "that have the below indicated eigenvalue in the selected range."
        ),
        "group": "Analyse",
    },
]
SELECT_EIGENVAL = Annotated[
    int,
    {
        "label": "Select on eigenvalue",
        "min": 1,
        "max": 20,
        "tooltip": (
            "This is the number of the eigenvalue to be used in the particle subset "
            "selection (start counting at 1)."
        ),
        "group": "Analyse",
    },
]
EIGENVAL_RANGE = Annotated[
    tuple[float, float],
    {
        "label": "Eigenvalue range",
        "tooltip": (
            "This is the minimum value for the selected eigenvalue; only particles "
            "with the selected eigenvalue within this range will be included in the "
            "output particles.star file."
        ),
        "group": "Analyse",
    },
]
