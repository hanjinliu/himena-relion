from typing import Annotated


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
            "The number of classes (K) for a multi-reference ab initio SGD refinement. "
            "These classes will be made in an unsupervised manner, starting from a "
            "single reference in the initial iterations of the SGD, and the references "
            "will become increasingly dissimilar during the inbetween iterations."
        ),
        "group": "Optimisation",
    },
]
SYM_NAME = Annotated[
    str,
    {
        "label": "Symmetry",
        "tooltip": (
            "The initial model is always generated in C1 and then aligned to and "
            "symmetrized with the specified point group. If the automatic alignment "
            "fails, please manually rotate run_itNNN_class001.mrc (NNN is the number "
            "of iterations) so that it conforms the symmetry convention."
        ),
        "group": "Optimisation",
    },
]

DO_RUN_C1 = Annotated[
    bool,
    {
        "label": "Run in C1 and apply symmetry later",
        "tooltip": (
            "If set to Yes, the gradient-driven optimisation is run in C1 and the "
            "symmetry orientation is searched and applied later. If set to No, the "
            "entire optimisation is run in the symmetry point group indicated above."
        ),
        "group": "Optimisation",
    },
]
DO_SOLVENT = Annotated[
    bool,
    {
        "label": "Flatten and enforce non-negative solvent",
        "tooltip": (
            "If set to Yes, the job will apply a spherical mask and enforce all values "
            "in the reference to be non-negative."
        ),
        "group": "Optimisation",
    },
]
