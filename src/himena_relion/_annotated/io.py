from typing import Annotated
from himena_relion._widgets._magicgui import PathDrop, OptimisationSetEdit

IN_MOVIES = Annotated[
    str,
    {
        "label": "Input movies",
        "widget_type": PathDrop,
        "type_label": ["MicrographMoviesData", "MicrographMovieGroupMetadata"],
        "allowed_extensions": [".mrc", ".mrcs", ".tif", ".tiff"],
        "group": "I/O",
    },
]
IN_MICROGRAPHS = Annotated[
    str,
    {
        "label": "Input micrographs",
        "widget_type": PathDrop,
        "type_label": ["MicrographsData", "MicrographGroupMetadata"],
        "allowed_extensions": [".mrc", ".mrcs", ".tif", ".tiff"],
        "group": "I/O",
    },
]
IN_COORDINATES = Annotated[
    str,
    {
        "label": "Input coordinates",
        "widget_type": PathDrop,
        "type_label": ["MicrographsCoords", "MicrographCoordsGroup"],
        "allowed_extensions": [".star"],
        "group": "I/O",
    },
]
IN_PARTICLES = Annotated[
    str,
    {
        "label": "Input particles",
        "widget_type": PathDrop,
        "type_label": ["ParticlesData", "ParticleGroupMetadata"],
        "allowed_extensions": [".star"],
        "group": "I/O",
    },
]
IN_PARTICELS_SUBTRACT = Annotated[
    str,
    {
        "label": "Use these particles instead",
        "widget_type": PathDrop,
        "type_label": ["ParticlesData", "ParticleGroupMetadata"],
        "allowed_extensions": [".star"],
        "group": "I/O",
    },
]
IMG_TYPE = Annotated[
    str,
    {
        "label": "Input images",
        "widget_type": PathDrop,
        "type_label": "ParticlesData",
        "allowed_extensions": [".star"],
        "group": "I/O",
    },
]
REF_TYPE = Annotated[
    str,
    {
        "label": "Reference map",
        "widget_type": PathDrop,
        "type_label": "DensityMap",
        "allowed_extensions": [".mrc", ".map"],
        "group": "I/O",
    },
]
MAP_TYPE = Annotated[
    str,
    {
        "label": "Input 3D map",
        "widget_type": PathDrop,
        "type_label": "DensityMap",
        "allowed_extensions": [".mrc", ".map"],
        "group": "I/O",
    },
]
HALFMAP_TYPE = Annotated[
    str,
    {
        "label": "One of the half-maps",
        "widget_type": PathDrop,
        "type_label": "DensityMap",
        "allowed_extensions": [".mrc", ".map"],
        "group": "I/O",
    },
]
IN_MASK = Annotated[
    str,
    {
        "label": "Reference mask (optional)",
        "widget_type": PathDrop,
        "type_label": "Mask3D",
        "allowed_extensions": [".mrc", ".map"],
        "group": "I/O",
    },
]
IN_MASK_SUBTRACT = Annotated[
    str,
    {
        "label": "Mask of the signal to keep",
        "widget_type": PathDrop,
        "type_label": "Mask3D",
        "allowed_extensions": [".mrc", ".map"],
        "tooltip": (
            "Provide a soft mask where the protein density you wish to subtract from "
            "the experimental particles is black (0) and the density you wish to keep "
            "is white (1)."
        ),
        "group": "I/O",
    },
]
PROCESS_TYPE = Annotated[
    str,
    {
        "label": "Input postprocess STAR",
        "widget_type": PathDrop,
        "type_label": "ProcessData",
        "allowed_extensions": [".star"],
        "group": "I/O",
    },
]
IN_OPTIMISER = Annotated[
    str,
    {
        "label": "Input optimiser STAR",
        "widget_type": PathDrop,
        "type_label": "OptimiserData",
        "allowed_extensions": [".star"],
        "group": "I/O",
    },
]
IN_TILT = Annotated[
    str,
    {
        "label": "Input tilt series",
        "widget_type": PathDrop,
        "type_label": "TomogramGroupMetadata",
        "allowed_extensions": [".star"],
        "group": "I/O",
    },
]

IN_OPTIM = Annotated[
    dict,
    {
        "label": "Input particles",
        "tooltip": "Input optimisation_set.star file.",
        "group": "I/O",
        "widget_type": OptimisationSetEdit,
    },
]

CONTINUE = Annotated[
    str,
    {
        "label": "Continue from here",
        "widget_type": PathDrop,
        "type_label": "ProcessData",
        "allowed_extensions": [".star"],
        "group": "I/O",
    },
]

DO_F16 = Annotated[
    bool,
    {
        "label": "Write output in float16",
        "tooltip": (
            "If set to Yes, this program will write output images in float16 format. "
            "This will save a factor of two in disk space compared to the default of "
            "writing in float32. Note that RELION and CCPEM will read float16 images, "
            "but other programs may not (yet) do so. For example, Gctf will not work "
            "with float16 images. Also note that this option does not work with UCSF "
            "MotionCor2. For CTF estimation, use CTFFIND-4.1 with pre-calculated power "
            "spectra (activate the 'Save sum of power spectra' option)."
        ),
        "group": "I/O",
    },
]
