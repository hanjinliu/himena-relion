from typing import Annotated

USE_NODW = Annotated[
    bool,
    {
        "label": "Use noDW micrographs",
        "tooltip": (
            "If set to Yes, the CTF estimation will be done using the micrograph "
            "without dose-weighting as in rlnMicrographNameNoDW (_noDW.mrc from "
            "MotionCor2). If set to No, the normal rlnMicrographName will be used."
        ),
        "group": "I/O",
    },
]
DO_PHASESHIFT = Annotated[
    bool,
    {
        "label": "Estimate phase shifts",
        "tooltip": (
            "If set to Yes, CTFFIND4 will estimate the phase shift, e.g. as introduced "
            "by a Volta phase-plate"
        ),
        "group": "I/O",
    },
]
PHASE_RANGE = Annotated[
    tuple[float, float, float],
    {
        "label": "Phase shift min/max/step (deg)",
        "tooltip": (
            "Minimum, maximum and step size (in degrees) for the search of the phase "
            "shift"
        ),
        "group": "I/O",
    },
]
DAST = Annotated[
    float,
    {
        "label": "Amount of astigmatism (A)",
        "tooltip": "CTFFIND's dAst parameter, GCTFs -astm parameter",
        "group": "I/O",
    },
]
# CTFFIND
USE_GIVEN_PS = Annotated[
    bool,
    {
        "label": "Use power spectra from MotionCorr",
        "tooltip": (
            "If set to Yes, the CTF estimation will be done using power spectra "
            "calculated during motion correction. You must use this option if you used "
            "float16 in motion correction."
        ),
        "group": "CTFFIND",
    },
]
SLOW_SEARCH = Annotated[
    bool,
    {
        "label": "Use exhaustive search",
        "tooltip": (
            "If set to Yes, CTFFIND4 will use slower but more exhaustive search. This "
            "option is recommended for CTFFIND version 4.1.8 and earlier, but probably "
            "not necessary for 4.1.10 and later. It is also worth trying this option "
            "when astigmatism and/or phase shifts are difficult to fit."
        ),
        "group": "CTFFIND",
    },
]
CTF_WIN = Annotated[
    int,
    {
        "label": "CTF estimation window size (pix)",
        "tooltip": (
            "If a positive value is given, a squared window of this size at the center "
            "of the micrograph will be used to estimate the CTF. This may be useful to "
            "exclude parts of the micrograph that are unsuitable for CTF estimation, "
            "e.g. the labels at the edge of phtographic film.\n\nThe original "
            "micrograph will be used (i.e. this option will be ignored) if a negative "
            "value is given."
        ),
        "group": "CTFFIND",
    },
]
BOX = Annotated[
    int,
    {
        "label": "FFT box size (pix)",
        "tooltip": "CTFFIND's Box parameter",
        "group": "CTFFIND",
    },
]
RESMAX = Annotated[
    float,
    {
        "label": "Resolution max (A)",
        "tooltip": "CTFFIND's ResMax parameter",
        "group": "CTFFIND",
    },
]
RESMIN = Annotated[
    float,
    {
        "label": "Resolution min (A)",
        "tooltip": "CTFFIND's ResMin parameter",
        "group": "CTFFIND",
    },
]
DFRANGE = Annotated[
    tuple[float, float, float],
    {
        "label": "Defocus search range min/max/step (A)",
        "tooltip": "CTFFIND's dFMin, dFMax and FStep parameters",
        "group": "CTFFIND",
    },
]

LOCALSEARCH_NOMINAL_DEFOCUS = Annotated[
    float,
    {
        "label": "Nominal defocus search range (A)",
        "tooltip": (
            "If a positive value is given, the defocus search range will be set to +/- "
            "this value (in A) around the nominal defocus value from the input STAR "
            "file. If a zero or negative value are given, then the overall min-max "
            "defocus search ranges above will be used instead."
        ),
        "group": "CTFFIND",
    },
]
EXP_FACTOR_DOSE = Annotated[
    float,
    {
        "label": "Dose-dependent Thon ring fading (e/A^2)",
        "tooltip": (
            "If a positive value is given, then the maximum resolution for CTF "
            "estimation is lowerered by exp(dose/this_factor) times the original "
            "maximum resolution specified above. Remember that exp(1) ~=2.7, so a "
            "value of 100 e/A^2 for this factor will yield 2.7x higher maxres for an "
            "accumulated dose of 100 e/A^2; Smaller values will lead to faster decay "
            "of the maxres. If zero or a negative value is given, the maximum value "
            "specified above will be used for all images."
        ),
        "group": "CTFFIND",
    },
]
