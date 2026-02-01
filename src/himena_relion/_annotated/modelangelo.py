from pathlib import Path
from typing import Annotated

from himena_relion._widgets._path_input import PathDrop


FN_MAP = Annotated[
    str,
    {
        "label": "B-factor sharpened map",
        "widget_type": PathDrop,
        "type_label": "DensityMap",
        "allowed_extensions": [".mrc", ".map"],
        "tooltip": (
            "Provide a (RELION-postprocessed) B-factor sharpened map for model building"
        ),
        "group": "I/O",
    },
]
P_SEQ = Annotated[
    Path,
    {
        "label": "FASTA sequence for proteins",
        "filter": "FASTA sequence files (*.fasta *.txt)",
        "tooltip": (
            "Provide a FASTA file with sequences for all protein chains to be built in "
            "the map. You can leave this empty if you don't know the proteins that are "
            "there, and then run a HMMer search to identify the unknown proteins. "
            "ModelAngelo will build much better models when provided with a FASTA "
            "sequence file!"
        ),
        "group": "I/O",
    },
]
D_SEQ = Annotated[
    Path,
    {
        "label": "FASTA sequence for DNA",
        "filter": "FASTA sequence files (*.fasta *.txt)",
        "tooltip": (
            "Provide a FASTA file with sequences for all DNA chains to be built in "
            "the map."
        ),
        "group": "I/O",
    },
]
R_SEQ = Annotated[
    Path,
    {
        "label": "FASTA sequence for RNA",
        "filter": "FASTA sequence files (*.fasta *.txt)",
        "tooltip": (
            "Provide a FASTA file with sequences for all RNA chains to be built in "
            "the map."
        ),
        "group": "I/O",
    },
]
GPU_ID = Annotated[
    str,
    {
        "label": "GPU ID",
        "tooltip": (
            "Provide a number for the GPU to be used (e.g. 0, 1 etc). Use "
            "comma-separated values to use multiple GPUs, e.g. 0,1,2"
        ),
        "group": "I/O",
    },
]
DO_HHMER = Annotated[
    bool,
    {
        "label": "Perform HMMer search?",
        "tooltip": (
            "If enabled, model-angelo will perform a HMM search using HMMer in "
            "the output directory of the model-angelo run (without sequence). You "
            "can continue an old run with this option switched on, and the model "
            "building step will be skipped if the output .cif exists. This way, "
            "you can try multiple HMMer runs."
        ),
        "group": "HMMer Search",
    },
]
FN_LIB = Annotated[
    Path,
    {
        "label": "Library with sequences for HMMer search",
        "filter": "FASTA sequence files (*.fasta *.txt)",
        "tooltip": (
            "FASTA file with library with all sequences for HMMer search. This is "
            "often an entire proteome."
        ),
        "group": "HMMer Search",
    },
]
ALPHABET = Annotated[
    str,
    {
        "label": "Alphabet for the HMMer search",
        "choices": ["amino", "DNA", "RNA"],
        "tooltip": "Type of Alphabet for HMM searches.",
        "group": "HMMer Search",
    },
]
F1 = Annotated[
    float,
    {
        "label": "HMMSearch F1",
        "tooltip": (
            "F1 parameter for HMMSearch, see their "
            "<a href=http://eddylab.org/software/hmmer/Userguide.pdf>documentation</a>."
        ),
        "group": "HMMer Search",
    },
]
F2 = Annotated[
    float,
    {
        "label": "HMMSearch F2",
        "tooltip": (
            "F2 parameter for HMMSearch, see their "
            "<a href=http://eddylab.org/software/hmmer/Userguide.pdf>documentation</a>."
        ),
        "group": "HMMer Search",
    },
]
F3 = Annotated[
    float,
    {
        "label": "HMMSearch F3",
        "tooltip": (
            "F3 parameter for HMMSearch, see their "
            "<a href=http://eddylab.org/software/hmmer/Userguide.pdf>documentation</a>."
        ),
        "group": "HMMer Search",
    },
]
E = Annotated[
    float,
    {
        "label": "HMMSearch E",
        "tooltip": (
            "E parameter for HMMSearch, see their "
            "<a href=http://eddylab.org/software/hmmer/Userguide.pdf>documentation</a>."
        ),
        "group": "HMMer Search",
    },
]
