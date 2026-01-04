from typing import Annotated

EXCLUDETILT_CACHE_SIZE = Annotated[
    int,
    {
        "label": "Number of cached tilt series",
        "min": 1,
        "max": 10,
        "tooltip": "This controls the number of cached tilt series in Napari.",
        "group": "I/O",
    },
]
TOMO_THICKNESS = Annotated[
    float,
    {
        "label": "Estimated tomogram thickness (nm)",
        "min": 1.0,
        "tooltip": (
            "Estimated tomogram thickness (in nm) to be used for projection matching "
            "in AreTomo2 and for patch tracking in IMOD"
        ),
        "group": "I/O",
    },
]


FIDUCIAL_DIAMETER = Annotated[
    float,
    {
        "label": "Fiducial diameter (nm)",
        "tooltip": "The diameter of the fiducials (in nm)",
        "min": 1,
        "group": "Alignment",
    },
]
PATCH_SIZE = Annotated[
    float,
    {
        "label": "Patch size (nm)",
        "min": 1,
        "tooltip": "The size of the patches in nanometer.",
        "group": "Alignment",
    },
]
PATCH_OVERLAP = Annotated[
    float,
    {
        "label": "Patch overlap (%)",
        "min": 0,
        "max": 100,
        "tooltip": "The overlap (0-100%) between the patches.",
        "group": "Alignment",
    },
]
DO_ARETOMO_TILTCORRECT = Annotated[
    bool,
    {
        "label": "Correct tilt angle offset",
        "tooltip": (
            "Specify Yes to correct the tilt angle offset in the tomogram (applies the "
            "AreTomo -TiltCor option). This is useful for correcting slanting in "
            "tomograms which can arise due to sample mounting or milling angle. This "
            "can be useful for in situ data."
        ),
        "group": "Alignment",
    },
]
ARETOMO_TILTCORRECT_ANGLE = Annotated[
    int | None,
    {
        "label": "Tilt angle offset",
        "tooltip": (
            "The tilt angle (in degrees) to be offset. If set to a value larger than "
            "180, AreTomo will search for the optimal value itself, otherwise the "
            "value specified here will be used."
        ),
        "group": "Alignment",
    },
]
DO_ARETOMO_CTF = Annotated[
    bool,
    {
        "label": "Estimate CTF",
        "tooltip": (
            "If set to Yes, AreTomo2 will also perform CTF estimation and any CTF "
            "information that was already present in the input STAR files will be "
            "overwritten. Note that when using this option, it is no longer necessary "
            "to run a CTF estimation job",
        ),
        "group": "Alignment",
    },
]
DO_ARETOMO_PHASESHIFT = Annotated[
    bool,
    {
        "label": "Estimate phase shift",
        "tooltip": (
            "If set to Yes, AreTomo2 will also perform estimation of the phase shift "
            "(due to a phase plate) during CTF estimation."
        ),
        "group": "Alignment",
    },
]
OTHER_ARETOMO_ARGS = Annotated[
    str,
    {
        "label": "Other AreTomo2 arguments",
        "tooltip": "Additional arguments that need to be passed to AreTomo2.",
        "group": "Alignment",
    },
]
GENERATE_SPLIT_TOMOGRAMS = Annotated[
    bool,
    {
        "label": "Split tomograms",
        "tooltip": (
            "Generate tomograms for input into a denoising job. For this option to "
            "work, Save images for denoising? should have been True during Motion "
            "Correction. Additionally, adjust zdim to minimise the amount of empty "
            "space without sample within the tomograms."
        ),
        "group": "I/O",
    },
]
DO_PROJ = Annotated[
    bool,
    {
        "label": "Write 2D projection",
        "tooltip": (
            "When set to Yes, this option will result in the calculation of 2D sums of "
            "Z-slices from the reconstructed tomograms. These may be useful to quickly "
            "screen for bad tomograms using the relion_display program."
        ),
        "group": "I/O",
    },
]
CENTRE_PROJ = Annotated[
    int,
    {
        "label": "Central Z-slice (binned pix)",
        "tooltip": (
            "This defines the central Z-slice of all Z-slices that will be summed to "
            "generate the 2D projection (in pixels in the tomogram). Zero means the "
            "middle (centre) of the tomogram."
        ),
        "group": "I/O",
    },
]
THICKNESS_PROJ = Annotated[
    int,
    {
        "label": "Number of Z-slices (binned pix)",
        "tooltip": (
            "This defines how many Z-slices will be summed to generate the 2D "
            "projection (in pixels in the tomogram). Half of the slices will be above "
            "and half will be below the central slice defined above."
        ),
        "group": "I/O",
    },
]


# Reconstruct
DIMS = Annotated[
    tuple[int, int, int],
    {
        "label": "Tomogram X, Y, Z size (unbinned pix)",
        "tooltip": "The tomogram X-, Y- and Z-dimensions in unbinned pixels.",
        "group": "Reconstruct",
    },
]
BINNED_ANGPIX = Annotated[
    float,
    {
        "label": "Pixel size (A)",
        "tooltip": (
            "The tomogram will be downscaled to this pixel size. For particle picking, "
            "often binning to pixel sizes of 5-10 A gives good enough tomograms. Note "
            "that the downsized tomograms are only used for picking; subsequent "
            "subtomogram averaging will not use these."
        ),
        "group": "Reconstruct",
    },
]
TILTANGLE_OFFSET = Annotated[
    float,
    {
        "label": "Tilt angle offset (deg)",
        "tooltip": (
            "The tomogram tilt angles will all be changed by this value. This may be "
            "useful to reconstruct lamellae that are all milled under a given angle. "
            "All tomograms will be reconstructed with the same offset. Use the "
            "tomogram name option below to reconstruct only a single tomogram."
        ),
        "group": "Reconstruct",
    },
]
TOMO_NAME = Annotated[
    str,
    {
        "label": "Reconstruct only this tomogram",
        "tooltip": (
            "If not left empty, the program will only reconstruct this particular "
            "tomogram"
        ),
        "group": "Reconstruct",
    },
]
# Filter
DO_FOURIER = Annotated[
    bool,
    {
        "label": "Fourier-inversion with odd/even frames",
        "tooltip": (
            "When set to Yes, a Wiener-filtered reconstruction will be calculated by "
            "Fourier inversion. The SNRs of all frames will be measured from the "
            "odd/even frames, which should have thus been calculated"
        ),
        "group": "Filter",
    },
]
CTF_INTACT_FIRST_PEAK = Annotated[
    bool,
    {
        "label": "Ignore CTFs until first peak",
        "tooltip": (
            "When set to Yes, the lowest spatial frequencies will not be boosted "
            "through CTF-correction, which will lead to a reconstruction with less "
            "low-resolution contrast, but better high-resolution details."
        ),
        "group": "Filter",
    },
]
