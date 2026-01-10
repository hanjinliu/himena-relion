from pathlib import Path
from typing import Annotated
from himena_relion._widgets._magicgui import DoseRateEdit

DO_RAW = Annotated[
    bool,
    {
        "label": "Import raw movies/micrographs?",
        "tooltip": ("Set this to Yes if you plan to import raw movies or micrographs"),
        "group": "I/O",
    },
]

FN_IN_RAW = Annotated[
    str,
    {
        "label": "Raw input files",
        "tooltip": (
            "Provide a Linux wildcard that selects all raw movies or micrographs to be "
            "imported. The path must be a relative path from the project directory. To "
            "import files outside the project directory, first make a symbolic link by "
            "an absolute path and then specify the link by a relative path. \n"
            "To process compressed MRC movies, you need pbzip2, zstd and xz command in "
            "your PATH for bzip2, Zstandard and xzip compression, respectively."
        ),
        "group": "I/O",
    },
]


OPTICS_GROUP_NAME = Annotated[
    str,
    {
        "label": "Optics group name",
        "tooltip": (
            "Name of this optics group. Each group of movies/micrographs with different "
            "optics characteristics for CTF refinement should have a unique name."
        ),
        "group": "I/O",
    },
]

FN_MTF = Annotated[
    str,
    {
        "label": "MTF of the detector",
        "tooltip": (
            "If you know the MTF of your detector, provide it here. Curves for some "
            "well-known detectors may be downloaded from the RELION Wiki. Also see "
            "there for the exact format\n If you do not know the MTF of your detector "
            "and do not want to measure it, then by leaving this entry empty, you "
            "include the MTF of your detector in your overall estimated B-factor upon "
            "sharpening the map. Although that is probably slightly less accurate, the "
            "overall quality of your map will probably not suffer very much. \n\n Note "
            "that when combining data from different detectors, the differences "
            "between their MTFs can no longer be absorbed in a single B-factor, and "
            "providing the MTF here is important!"
        ),
        "group": "I/O",
    },
]

ANGPIX = Annotated[
    float,
    {
        "label": "Pixel size (A)",
        "min": 0.01,
        "tooltip": "Pixel size in Angstroms.",
        "group": "I/O",
    },
]

KV = Annotated[
    int,
    {
        "label": "Voltage (kV)",
        "tooltip": "Voltage the microscope was operated on (in kV)",
        "group": "Optics",
    },
]

CS = Annotated[
    float,
    {
        "label": "Spherical aberration (mm)",
        "tooltip": (
            "Spherical aberration of the microscope used to collect these images (in "
            "mm). Typical values are 2.7 (FEI Titan & Talos, most JEOL CRYO-ARM), 2.0 "
            "(FEI Polara), 1.4 (some JEOL CRYO-ARM) and 0.01 (microscopes with a Cs "
            "corrector)."
        ),
        "group": "Optics",
    },
]

Q0 = Annotated[
    float,
    {
        "label": "Amplitude contrast",
        "min": 0.0,
        "tooltip": (
            "Fraction of amplitude contrast. Often values around 10% work better than "
            "theoretically more accurate lower values..."
        ),
        "group": "Optics",
    },
]

BEAM_TILT_X = Annotated[
    float,
    {
        "label": "Beamtilt in X (mrad)",
        "min": -1.0,
        "tooltip": "Known beamtilt in the X-direction (in mrad). Set to 0 if unknown.",
        "group": "Optics",
    },
]

BEAM_TILT_Y = Annotated[
    float,
    {
        "label": "Beamtilt in Y (mrad)",
        "min": -1.0,
        "tooltip": "Known beamtilt in the Y-direction (in mrad). Set to 0 if unknown.",
        "group": "Optics",
    },
]

FN_IN_OTHER = Annotated[
    str,
    {
        "label": "Input file(s) to import",
        "tooltip": (
            "Select any file(s) to import.\n\n Note that for importing coordinate "
            "files, one has to give a Linux wildcard, where the *-symbol is before the "
            "coordinate-file suffix, e.g. if the micrographs are called mic1.mrc and "
            "the coordinate files mic1.box or mic1_autopick.star, one HAS to give "
            "'*.box' or '*_autopick.star', respectively.\n\n Also note that "
            "micrographs, movies and coordinate files all need to be in the same "
            "directory (with the same rootnames, e.g.mic1 in the example above) in "
            "order to be imported correctly. 3D masks or references can be imported "
            "from anywhere. \n\nNote that movie-particle STAR files cannot be imported "
            "from a previous version of RELION, as the way movies are handled has "
            "changed in RELION-2.0. \n\nFor the import of a particle, 2D references or "
            "micrograph STAR file or of a 3D reference or mask, only a single file can "
            "be imported at a time. \n\nNote that due to a bug in a fltk library, you "
            "cannot import from directories that contain a substring  of the current "
            "directory, e.g. dont important from /home/betagal if your current "
            "directory is called /home/betagal_r2. In this case, just change one of "
            "the directory names."
        ),
        "group": "I/O",
    },
]

NODE_TYPE = Annotated[
    str,
    {
        "label": "Node type",
        "tooltip": "Select the type of Node this is.",
        "choices": [
            "Particle coordinates (*.box, *_pick.star)",
            "Particles STAR file (*.star)",
            "Multiple (2D or 3D) references (.star or .mrcs)",
            "3D reference (.mrc)",
            "3D mask (.mrc)",
            "Unfiltered half-map (unfil.mrc)",
        ],
        "widget_type": "RadioButtons",
        "group": "I/O",
    },
]

OPTICS_GROUP_PARTICLES = Annotated[
    str,
    {
        "label": "Rename optics group for particles",
        "tooltip": (
            "Only for the import of a particles STAR file with a single, or no, "
            "optics groups defined: rename the optics group for the imported particles "
            "to this string."
        ),
        "group": "I/O",
    },
]

# Tomo
MOVIE_FILES = Annotated[
    str,
    {
        "label": "Tilt image files",
        "tooltip": (
            "File pattern matching all tilt image files. These can be multi-frame "
            "micrographs or single 2D images."
        ),
        "group": "General",
    },
]
IMAGES_ARE_MOTION_CORRECTED = Annotated[
    bool,
    {
        "label": "Movies already motion corrected",
        "tooltip": (
            "Select Yes if your input images in 'Tilt image movie files' have already "
            "been motion corrected and/or are summed single frame images. Make sure "
            "the image file names match the corresponding image file names under "
            "SubFramePath in the mdoc files"
        ),
        "group": "General",
    },
]
MDOC_FILES = Annotated[
    str,
    {
        "label": "mod files",
        "tooltip": "File pattern pointing to the mdoc files.",
        "group": "General",
    },
]
PREFIX = Annotated[
    str,
    {
        "label": "Prefix",
        "tooltip": (
            "Optional prefix added to avoid tilt-series name collisions when dealing "
            "with multiple datasets."
        ),
        "group": "General",
    },
]
# Tilt series
DOSE_RATE_VALUE = Annotated[
    dict,
    {
        "label": "Dose rate (e/A^2)",
        "widget_type": DoseRateEdit,
        "tooltip": (
            "Electron dose (in e/A^2) per image in the tilt series, or the dose rate "
            "per movie frame."
        ),
        "group": "Tilt series",
    },
]
TILT_AXIS_ANGLE = Annotated[
    float,
    {
        "label": "Tilt axis angle (deg)",
        "tooltip": (
            "Nominal value for the tilt-axis rotation angle (positive is CCW from Y)"
        ),
        "group": "Tilt series",
    },
]
FLIP_TILTSERIES_HAND = Annotated[
    bool,
    {
        "label": "Invert defocus handedness",
        "tooltip": (
            "Specify Yes to flip the handedness of the defocus geometry (default = Yes "
            "(value -1 in the STAR file), the same as the tutorial dataset: "
            "EMPIAR-10164)"
        ),
        "group": "Tilt series",
    },
]

IN_COORDS = Annotated[
    Path,
    {
        "label": "Input coordinates",
        "filter": "STAR files (*.star);;All files (*)",
        "tooltip": (
            "You can provide a 2-column STAR file (with columns rlnTomoName and "
            "rlnTomoImportParticleFile for the tomogram names and their corrsesponding "
            "particle coordinate files, OR you can provide a linux wildcard to all the "
            "particle coordinate files.\n\nThe coordinate files can be in RELION STAR "
            "format, or in ASCII text files. Input STAR file should contain either "
            "rlnCoordinateX/Y/Z columns with non-centered coordinates in pixels of the "
            "tilt series, or rlnCenteredCoordinateX/Y/ZAngst column with coordinates "
            "in Angstroms from the center of the tomograms).\n\nASCII files may "
            "contain headers, but all lines where the first 3 columns contain numbers "
            "will be interpreted as data lines. The first 3 columns are assumed to be "
            "X, Y and Z coordinates. If 6 columns are present, columns 4,5 and 6 are "
            "assumed to be the rlnTomoSubtomogramRot/Tilt/Psi.\n\nFor text files, the "
            "options below are used to indicate whether the coordinates are relative "
            "to the centre of the tomogram (in which case they need to be provided in "
            "Angstroms, or converted thereto using a pixel size). Or if the "
            "coordinates are decentered, they need to be provided in pixels of the "
            "tilt series, possibly using a multiplicative scaling factor."
        ),
        "group": "Coordinates",
    },
]

REMOVE_SUBSTRING = Annotated[
    str,
    {
        "label": "Remove substring from file names",
        "tooltip": (
            "If specified, this substring is removed from the coordinate filenames to "
            "get the tomogram names"
        ),
        "group": "Coordinates",
    },
]
REMOVE_SUBSTRING2 = Annotated[
    str,
    {
        "label": "Second substring to remove",
        "tooltip": (
            "If specified, this substring is removed from the coordinate filenames to "
            "get the tomogram names"
        ),
        "group": "Coordinates",
    },
]
IS_CENTERED = Annotated[
    bool,
    {
        "label": "Coordinates are centered",
        "tooltip": (
            "Specify Yes if coordinates in the input text files are relative to the "
            "center of the tomogram."
        ),
        "group": "Coordinates",
    },
]
SCALE_FACTOR = Annotated[
    float,
    {
        "label": "Multiply coordinates with",
        "tooltip": (
            "As also mentioned above, centered coordinates should be in Angstroms, "
            "decentered coordinates should be in pixels of the (motion-corrected) tilt "
            "series. If they are not, multiply them with this factor to convert them."
        ),
        "group": "Coordinates",
    },
]
ADD_FACTOR = Annotated[
    float,
    {
        "label": "Add this to coordinates",
        "tooltip": (
            "After conversion of coordinates in text files to centered coordinates in "
            "Angstroms, or decentered coordinates in pixels of the tilt series, add "
            "this factor the coordinate values."
        ),
        "group": "Coordinates",
    },
]
