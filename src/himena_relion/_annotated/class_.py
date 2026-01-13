from typing import Annotated
from himena_relion._widgets._magicgui import Class2DAlgorithmEdit

NUM_ITER = Annotated[
    int,
    {
        "label": "Number of iterations",
        "min": 1,
        "tooltip": (
            "How many iterations (i.e. mini-batches) to perform with the VDAM "
            "algorithm?"
        ),
        "group": "Optimisation",
    },
]
NUM_CLASS = Annotated[
    int,
    {
        "label": "Number of classes",
        "min": 1,
        "tooltip": (
            "The number of classes (K) for a multi-reference refinement. These classes "
            "will be made in an unsupervised manner from a single reference by "
            "division of the data into random subsets during the first iteration."
        ),
        "group": "Optimisation",
    },
]

HIGH_RES_LIMIT = Annotated[
    float | None,
    {
        "label": "High-resolution limit (A)",
        "tooltip": (
            "If set, then the expectation step (i.e. the alignment) will be done only "
            "including the Fourier components up to this resolution (in Angstroms). "
            "This is useful to prevent overfitting, as the "
            "classification runs in RELION are not to be guaranteed to be 100% "
            "overfitting-free (unlike the 3D auto-refine with its gold-standard FSC). "
            "In particular for very difficult data sets, e.g. of very small or "
            "featureless particles, this has been shown to give much better class "
            "averages. In such cases, values in the range of 7-12 Angstroms have "
            "proven useful."
        ),
        "min": 0.0,
        "group": "Optimisation",
    },
]

OPTIM_ALGORIGHM = Annotated[
    dict,
    {
        "label": "Algorithm",
        "widget_type": Class2DAlgorithmEdit,
        "tooltip": (
            "The optimization algorithm to use:\n\n"
            "<b>EM:</b> the slower expectation-maximization algorithm will be used. "
            "This was the default option in releases prior to 4.0-beta. The current "
            "implementation of 2D class averaging and 3D classification does NOT "
            "comprise a convergence criterium. Therefore, the calculations will "
            "need to be stopped by the user if further iterations do not yield "
            "improvements in resolution or classes.\n\n"
            "<b>VDAM:</b> the faster VDAM algorithm will be used. This algorithm was "
            "introduced with relion-4.0. Using 200 iterations has given good results "
            "for many data sets. Using 100 will run faster, at the expense of some "
            "quality in the results."
        ),
        "group": "Optimisation",
    },
]
DO_CENTER = Annotated[
    bool,
    {
        "label": "Center class averages",
        "tooltip": (
            "If set to Yes, every iteration the class average images will be centered "
            "on their center-of-mass. This will only work for positive signals, so the "
            "particles should be white."
        ),
        "group": "Optimisation",
    },
]
PSI_SAMPLING = Annotated[
    float,
    {
        "label": "In-plane angular sampling (deg)",
        "tooltip": (
            "The sampling rate for the in-plane rotation angle (psi) in degrees. Using "
            "fine values will slow down the program. Recommended value for most 2D "
            "refinements: 5 degrees.\n\nIf auto-sampling is used, this will be the "
            "value for the first iteration(s) only, and the sampling rate will be "
            "increased automatically after that."
        ),
        "group": "Sampling",
    },
]

DO_HELIX = Annotated[
    bool,
    {
        "label": "Classify 2D helical segments",
        "tooltip": (
            "Set to Yes if you want to classify 2D helical segments. Note that the "
            "helical segments should come with priors of psi angles"
        ),
        "group": "Helix",
    },
]
DO_BIMODAL_PSI = Annotated[
    bool,
    {
        "label": "Do bimodal angular searches",
        "tooltip": (
            "Do bimodal search for psi angles. Set to Yes if you want to classify 2D "
            "helical segments with priors of psi angles. The priors should be bimodal "
            "due to unknown polarities of the segments. Set to No if the 3D helix "
            "looks the same when rotated upside down. If it is set to No, ordinary "
            "angular searches will be performed.\n\nThis option will be invalid if "
            "you choose not to perform image alignment."
        ),
        "group": "Helix",
    },
]
RANGE_PSI = Annotated[
    float,
    {
        "label": "Angular search range (deg)",
        "tooltip": (
            "Local angular searches will be performed within +/- the given amount (in "
            "degrees) from the psi priors estimated through helical segment picking. A "
            "range of 15 degrees is the same as sigma = 5 degrees. Note that the "
            "ranges of angular searches should be much larger than the sampling. \n\n"
            "This option will be invalid if you choose not to perform image alignment."
        ),
        "group": "Helix",
    },
]
DO_RESTRICT_XOFF = Annotated[
    bool,
    {
        "label": "Restrict helical offsets to rise",
        "tooltip": (
            "Set to Yes if you want to restrict the translational offsets along the "
            "helices to the rise of the helix given below. Set to No to allow free "
            "(conventional) translational offsets."
        ),
        "group": "Helix",
    },
]
