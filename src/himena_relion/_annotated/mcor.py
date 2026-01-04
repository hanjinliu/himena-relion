from typing import Annotated

FIRST_FRAME_SUM = Annotated[
    int,
    {
        "label": "First frame for corrected sum",
        "tooltip": ("First frame to use in corrected average (starts counting at 1)."),
        "group": "I/O",
    },
]
LAST_FRAME_SUM = Annotated[
    int,
    {
        "label": "Last frame for corrected sum",
        "tooltip": (
            "Last frame to use in corrected average. Values equal to or smaller than 0 "
            "mean 'use all frames'."
        ),
        "group": "I/O",
    },
]
DOSE_PER_FRAME = Annotated[
    float,
    {
        "label": "Dose per frame (e/A^2)",
        "tooltip": "Dose per movie frame (in electrons per squared Angstrom).",
        "group": "I/O",
    },
]
PRE_EXPOSURE = Annotated[
    float,
    {
        "label": "Pre-exposure (e/A^2)",
        "tooltip": "Pre-exposure dose (in electrons per squared Angstrom).",
        "group": "I/O",
    },
]
EER_FRAC = Annotated[
    int,
    {
        "label": "EER fractionation",
        "min": 1,
        "tooltip": (
            "The number of hardware frames to group into one fraction. This option is "
            "relevant only for Falcon4 movies in the EER format. Note that all 'frames'"
            " in the GUI (e.g. first and last frame for corrected sum, dose per frame) "
            "refer to fractions, not raw detector frames."
        ),
        "group": "I/O",
    },
]
DO_F16 = Annotated[
    bool,
    {
        "label": "Write output in float16",
        "tooltip": (
            "If set to Yes, RelionCor2 will write output images in float16 MRC format. "
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
DO_DOSE_WEIGHTING = Annotated[
    bool,
    {
        "label": "Do dose-weighting",
        "tooltip": "If set to Yes, the averaged micrographs will be dose-weighted.",
        "group": "I/O",
    },
]
DO_SAVE_NO_DW = Annotated[
    bool,
    {
        "label": "Save non-dose weighted as well",
        "tooltip": (
            "Aligned but non-dose weighted images are sometimes useful in CTF "
            "estimation, although there is no difference in most cases. Whichever the "
            "choice, CTF refinement job is always done on dose-weighted particles."
        ),
        "group": "I/O",
    },
]
DO_SAVE_PS = Annotated[
    bool,
    {
        "label": "Save sum of power spectra",
        "tooltip": (
            "Sum of non-dose weighted power spectra provides better signal for CTF "
            "estimation. The power spectra can be used by CTFFIND4 but not by GCTF. "
            "This option is not available for UCSF MotionCor2. You must use this "
            "option when writing in float16."
        ),
        "group": "I/O",
    },
]
SUM_EVERY_E = Annotated[
    float,
    {
        "label": "Sum power spectra every (e/A^2)",
        "tooltip": (
            "McMullan et al (Ultramicroscopy, 2015) suggest summing power spectra "
            "every 4.0 e/A2 gives optimal Thon rings"
        ),
        "group": "I/O",
    },
]
BFACTOR = Annotated[
    float,
    {
        "label": "Bfactor",
        "tooltip": "The B-factor that will be applied to the micrographs.",
        "group": "Motion Correction",
    },
]
GROUP_FRAMES = Annotated[
    int,
    {
        "label": "Group frames",
        "min": 1,
        "tooltip": (
            "Average together this many frames before calculating the beam-induced "
            "shifts."
        ),
        "group": "Motion Correction",
    },
]
BIN_FACTOR = Annotated[
    int,
    {
        "label": "Binning factor",
        "min": 1,
        "tooltip": (
            "Bin the micrographs this much by a windowing operation in the Fourier "
            "Tranform. Binning at this level is hard to un-do later on, but may be "
            "useful to down-scale super-resolution images. Float-values may be used. "
            "Do make sure though that the resulting micrograph size is even."
        ),
        "group": "Motion Correction",
    },
]
DEFECT_FILE = Annotated[
    str,
    {
        "label": "Defect file",
        "tooltip": (
            "Location of a UCSF MotionCor2-style defect text file or a defect map that "
            "describe the defect pixels on the detector. Each line of a defect text "
            "file should contain four numbers specifying x, y, width and height of a "
            "defect region. A defect map is an image (MRC or TIFF), where 0 means good "
            "and 1 means bad pixels. The coordinate system is the same as the input "
            "movie before application of binning, rotation and/or flipping.\nNote that "
            "the format of the defect text is DIFFERENT from the defect text produced "
            "by SerialEM! One can convert a SerialEM-style defect file into a defect "
            'map using IMOD utilities e.g. "clip defect -D defect.txt -f tif '
            'movie.mrc defect_map.tif". See explanations in the SerialEM manual.\n\n'
            "Leave empty if you don't have any defects, or don't want to correct for "
            "defects on your detector."
        ),
        "group": "Motion Correction",
    },
]
GAIN_REF = Annotated[
    str,
    {
        "label": "Gain reference image",
        "tooltip": (
            "Location of the gain-reference file to be applied to the input "
            "micrographs. Leave this empty if the movies are already gain-corrected."
        ),
        "group": "Motion Correction",
    },
]
GAIN_ROT = Annotated[
    str,
    {
        "choices": [
            "No rotation (0)",
            "90 degrees (1)",
            "180 degrees (2)",
            "270 degrees (3)",
        ],
        "label": "Gain reference flipping",
        "tooltip": (
            "Rotate the gain reference by this number times 90 degrees clockwise in "
            "relion_display. This is the same as -RotGain in MotionCor2. Note that "
            "MotionCor2 uses a different convention for rotation so it says 'counter-"
            "clockwise'. Valid values are 0, 1, 2 and 3."
        ),
        "group": "Motion Correction",
    },
]
GAIN_FLIP = Annotated[
    str,
    {
        "choices": [
            "No flipping (0)",
            "Flip upside down (1)",
            "Flip left to right (2)",
        ],
        "label": "Gain reference flipping",
        "tooltip": (
            "Flip the gain reference after rotation. This is the same as -FlipGain in "
            "MotionCor2. 0 means do nothing, 1 means flip Y (upside down) and 2 means "
            "flip X (left to right)."
        ),
        "group": "Motion Correction",
    },
]
PATCH = Annotated[
    tuple[int, int],
    {
        "label": "Number of patches (X, Y)",
        "tooltip": "Number of patches (in X and Y direction) to apply motioncor2.",
        "group": "Motion Correction",
    },
]

DO_ODD_EVEN_SPLIT = Annotated[
    bool,
    {
        "label": "Save images for denoising",
        "tooltip": (
            "If set to Yes, MotionCor2 will write output images summed from both the "
            "even frames of the input movie and the odd frames of the input movie. "
            "This generates two versions of the same movie which essential if you wish "
            "to carry out denoising later. If you are unsure whether you will need "
            "denoising later, it is best to select Yes, but be aware this option "
            "increases the processing time for MotionCor. At the moment, this is only "
            "available in Shawn Zheng's MotionCor2 (>=v1.3.0)  and therefore "
            "do_float_16 must equal false too."
        ),
        "group": "I/O",
    },
]
SUM_EVERY_N = Annotated[
    int,
    {
        "label": "Save power spectra every n frames",
        "tooltip": (
            "McMullan et al (Ultramicroscopy, 2015) suggest summing power spectra "
            "every 4.0 e/A2 gives optimal Thon rings"
        ),
        "group": "I/O",
    },
]

EER_GROUPING = Annotated[
    int,
    {
        "label": "EER grouping",
        "min": 1,
        "tooltip": (
            "The number of hardware frames to group into one fraction. This option is "
            "relevant only for Falcon4 movies in the EER format. Note that all "
            "'frames' in the GUI (e.g. first and last frame for corrected sum, dose "
            "per frame) refer to fractions, not raw detector frames."
        ),
    },
]

OTHER_MOTIONCOR2_ARGS = Annotated[
    str,
    {
        "label": "Other MotionCor2 arguments",
        "tooltip": ("Additional arguments that need to be passed to MOTIONCOR2."),
        "group": "Motion Correction",
    },
]
