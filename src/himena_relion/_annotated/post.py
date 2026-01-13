from typing import Annotated

# mask creation
LOWPASS_FILTER = Annotated[
    float,
    {
        "label": "Lowpass filter (A)",
        "tooltip": (
            "Lowpass filter that will be applied to the input map, prior to "
            "binarization. To calculate solvent masks, a lowpass filter of 15-20A may "
            "work well."
        ),
        "group": "Mask",
    },
]
ANGPIX_MASK = Annotated[
    float | None,
    {
        "label": "Pixel size (A)",
        "tooltip": (
            "Provide the pixel size of the input map in Angstroms to calculate the "
            "low-pass filter. This value is also used in the output image header."
        ),
        "group": "Mask",
    },
]
INIMASK_THRESHOLD = Annotated[
    float,
    {
        "label": "Initial binarisation threshold",
        "tooltip": (
            "This threshold is used to make an initial binary mask from the average of "
            "the two unfiltered half-reconstructions. If you don't know what value to "
            "use, display one of the unfiltered half-maps in a 3D surface rendering "
            "viewer and find the lowest threshold that gives no noise peaks outside "
            "the reconstruction."
        ),
        "group": "Mask",
    },
]
EXTEND_INIMASK = Annotated[
    int,
    {
        "label": "Extend binary map (pixels)",
        "tooltip": (
            "The initial binary mask is extended this number of pixels in all "
            "directions."
        ),
        "group": "Mask",
        "min": 0,
    },
]
WIDTH_MASK_EDGE = Annotated[
    int,
    {
        "label": "Soft edge (pixels)",
        "tooltip": (
            "The extended binary mask is further extended with a raised-cosine soft "
            "edge of the specified width."
        ),
        "group": "Mask",
        "min": 0,
    },
]

# post process

ANGPIX_POST = Annotated[
    float | None,
    {
        "label": "Calibrated pixel size (A)",
        "tooltip": (
            "Provide the final, calibrated pixel size in Angstroms. This value may be "
            "different from the pixel-size used thus far, e.g. when you have "
            "recalibrated the pixel size using the fit to a PDB model. The X-axis of "
            "the output FSC plot will use this calibrated value."
        ),
        "group": "I/O",
    },
]
DO_SKIP_FSC_WEIGHTING = Annotated[
    bool,
    {
        "label": "Skip FSC-weighting",
        "tooltip": (
            "If set to No (the default), then the output map will be low-pass filtered "
            "according to the mask-corrected, gold-standard FSC-curve. Sometimes, it "
            "is also useful to provide an ad-hoc low-pass filter (option below), as "
            "due to local resolution variations some parts of the map may be better "
            "and other parts may be worse than the overall resolution as measured by "
            "the FSC. In such cases, set this option to Yes and provide an ad-hoc "
            "filter as described below."
        ),
        "group": "Sharpen",
    },
]
LOW_PASS = Annotated[
    float,
    {
        "label": "Low-pass filter (A)",
        "tooltip": (
            "This option allows one to low-pass filter the map at a user-provided "
            "frequency (in Angstroms). When using a resolution that is higher than the "
            "gold-standard FSC-reported resolution, take care not to interpret noise "
            "in the map for signal..."
        ),
        "group": "Sharpen",
    },
]
FN_MTF = Annotated[
    str,
    {
        "label": "MTF of the detector",
        "tooltip": (
            "If you know the MTF of your detector, provide it here. Curves for some "
            "well-known detectors may be downloaded from the RELION Wiki. Also see "
            "there for the exact format.\n If you do not know the MTF of your detector "
            "and do not want to measure it, then by leaving this entry empty, you "
            "include the MTF of your detector in your overall estimated B-factor upon "
            "sharpening the map. Although that is probably slightly less accurate, the "
            "overall quality of your map will probably not suffer very much."
        ),
        "group": "Sharpen",
    },
]
MTF_ANGPIX = Annotated[
    float,
    {
        "label": "MTF pixel size (A)",
        "tooltip": (
            "This is the original pixel size (in Angstroms) in the raw "
            "(non-super-resolution!) micrographs."
        ),
        "group": "Sharpen",
    },
]
