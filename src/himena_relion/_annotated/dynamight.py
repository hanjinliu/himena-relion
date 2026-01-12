from pathlib import Path
from typing import Annotated

from himena_relion._widgets._path_input import PathDrop

FN_STAR = Annotated[
    str,
    {
        "label": "Input images STAR file",
        "widget_type": PathDrop,
        "type_label": ["ParticlesData", "ParticleGroupMetadata"],
        "tooltip": (
            "A STAR file with all images (and their metadata).\n"
            "You can use spi or mrcs image stacks (not recommended, read help!)"
        ),
        "group": "I/O",
    },
]
FN_MAP = Annotated[
    str,
    {
        "label": "Consensus map",
        "widget_type": PathDrop,
        "type_label": "DensityMap",
        "tooltip": (
            "A 3D map in MRC/Spider format. Make sure this map has the same dimensions "
            "and the same pixel size as your input images."
        ),
        "group": "I/O",
    },
]
NR_GAUSSIANS = Annotated[
    int,
    {
        "label": "Number of Gaussians",
        "tooltip": (
            "Number of Gaussians to describe the consensus map with. Larger structures "
            "that one wishes to describe at higher resolutions will need more "
            "Gaussians. As a rule of thumb, you could try and use 1-2 Gaussians per "
            "amino acid or nucleotide in your complex. But note that running DynaMight "
            "with more than 30,000 Gaussians may be problematic on GPUs with a memory "
            "of 24 GB."
        ),
        "group": "Model Parameters",
    },
]
INITIAL_THRESHOLD = Annotated[
    float | None,
    {
        "label": "Initial map threshold",
        "tooltip": (
            "If provided, this threshold will be used to position initial Gaussians in "
            "the consensus map. If left empty, an automated procedure will be used to "
            "estimate the appropriate threshold."
        ),
        "group": "Model Parameters",
    },
]
REG_FACTOR = Annotated[
    float,
    {
        "label": "Regularization factor",
        "tooltip": (
            "This regularization factor defines the relative weights between the data "
            "over the restraints. Values higher than one will put more weights on the "
            "restraints."
        ),
        "group": "Model Parameters",
    },
]
GPU_ID = Annotated[
    str,
    {
        "label": "GPU ID (single GPU only)",
        "tooltip": (
            "Note that DynaMight can only use one GPU at a time. Data sets with many "
            "particles or large box sizes will require powerful GPUs, like an A100."
        ),
        "group": "Computation",
    },
]
DO_PRELOAD = Annotated[
    bool,
    {
        "label": "Preload images in RAM",
        "tooltip": (
            "If enabled, dynamight will preload images into memory for learning the "
            "forward or inverse deformations and for deformed backprojection. This "
            "will speed up the calculations, but you need to make sure you have enough "
            "RAM to do so."
        ),
        "group": "Computation",
    },
]
IN_CHECKPOINT = Annotated[
    Path,
    {
        "label": "Checkpoint file",
        "tooltip": (
            "Select the checkpoint file to use for visualization, inverse deformation "
            "estimation or deformed backprojection. If left empty, the last available "
            "checkpoint file will be used"
        ),
        "group": "I/O",
    },
]
HALFSET = Annotated[
    int,
    {
        "label": "Half-set to visualize",
        "tooltip": (
            "Select halfset 1 or 2 to explore the latent space of that halfset. If you "
            "select halfset 0, then the validation set is being visualised, which will "
            "give you an estimate of the errors in the deformations."
        ),
        "choices": [("validation set", 0), ("halfset 1", 1), ("halfset 2", 2)],
        "group": "Visualization",
    },
]
NR_EPOCHS = Annotated[
    int,
    {
        "label": "Number of epochs to perform",
        "tooltip": (
            "Number of epochs to perform inverse deformations. You can monitor the "
            "convergence of the loss function to assess how many are necessary. Often "
            "200 are enough"
        ),
        "group": "Inverse Deformation Estimation",
    },
]
DO_STORE_DEFORM = Annotated[
    bool,
    {
        "label": "Store deformations in RAM",
        "tooltip": (
            "If enabled, dynamight will store deformations in the GPU memory, which "
            "will speed up the calculations, but you need to have enough GPU memory to "
            "do this..."
        ),
        "group": "Inverse Deformation Estimation",
    },
]
BACKPROJECT_BATCHSIZE = Annotated[
    int,
    {
        "label": "Backprojection batchsize",
        "tooltip": (
            "Number of images to process in parallel. This will speed up the "
            "calculation, but will cost GPU memory. Try how high you can go on your "
            "GPU, given your box size and size of the neural network."
        ),
        "group": "Deformed Backprojection",
    },
]
