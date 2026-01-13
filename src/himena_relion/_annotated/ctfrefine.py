from typing import Annotated

FIT_CTF_CHOICES = ["No", "Per-micrograph", "Per-particle"]

DO_DEFOCUS = Annotated[
    str,
    {
        "label": "Fit defocus",
        "tooltip": (
            "If set to per-particle or per-micrograph, then relion_ctf_refine will "
            "estimate defocus values."
        ),
        "choices": FIT_CTF_CHOICES,
        "group": "Fit",
    },
]
DO_ASTIG = Annotated[
    str,
    {
        "label": "Fit astigmatism",
        "tooltip": (
            "If set to per-particle or per-micrograph, then relion_ctf_refine will "
            "estimate astigmatism."
        ),
        "choices": FIT_CTF_CHOICES,
        "group": "Fit",
    },
]
DO_BFACTOR = Annotated[
    str,
    {
        "label": "Fit B-factor",
        "tooltip": (
            "If set to per-particle or per-micrograph, then relion_ctf_refine will "
            "estimate B-factors that describe the signal falloff."
        ),
        "choices": FIT_CTF_CHOICES,
        "group": "Fit",
    },
]
DO_PHASE = Annotated[
    str,
    {
        "label": "Fit phase shift",
        "tooltip": (
            "If set to per-particle or per-micrograph, then relion_ctf_refine will "
            "estimate (VPP?) phase shift values."
        ),
        "choices": FIT_CTF_CHOICES,
        "group": "Fit",
    },
]
DO_TILT = Annotated[
    bool,
    {
        "label": "Estimate beam tilt",
        "tooltip": (
            "If enabled, then relion_ctf_refine will also estimate the beamtilt per "
            "optics group. This option is only recommended for data sets that extend "
            "beyond 4.5 Angstrom resolution."
        ),
        "group": "Fit",
    },
]
DO_TREFOIL = Annotated[
    bool,
    {
        "label": "Estimate trefoil",
        "tooltip": (
            "If enabled, then relion_ctf_refine will also estimate the trefoil "
            "(3-fold astigmatism) per optics group. This option is only recommended "
            "for data sets that extend beyond 3.5 Angstrom resolution."
        ),
        "group": "Fit",
    },
]
DO_4THORDER = Annotated[
    bool,
    {
        "label": "Estimate 4th order aberrations",
        "tooltip": (
            "If enabled, then relion_ctf_refine will also estimate the Cs and the "
            "tetrafoil (4-fold astigmatism) per optics group. This option is only "
            "recommended for data sets that extend beyond 3 Angstrom resolution."
        ),
        "group": "Fit",
    },
]
MINRES = Annotated[
    float,
    {
        "label": "Minimum resolution for fitting (A)",
        "tooltip": (
            "The minimum spatial frequency (in Angstrom) used in the beamtilt fit."
        ),
        "group": "Fit",
    },
]

# Tomogram
BOX_SIZE = Annotated[
    int,
    {
        "label": "Box size of estimation (pix)",
        "tooltip": (
            "Box size to be used for the estimation. Note that this can be larger than "
            "the box size of the reference map. A sufficiently large box size allows "
            "more of the high-frequency signal to be captured that has been "
            "delocalised by the CTF."
        ),
        "group": "Defocus",
    },
]
DO_DEFOCUS_TOMO = Annotated[
    bool,
    {
        "label": "Refine defocus",
        "tooltip": (
            "If set to per-particle or per-micrograph, then relion_ctf_refine will "
            "estimate defocus values."
        ),
        "group": "Defocus",
    },
]
FOCUS_RANGE = Annotated[
    float,
    {
        "label": "Defocus search range (A)",
        "tooltip": (
            "Defocus search range (in A). This search range will be, by default, "
            "sampled in 100 steps. Use the additional argument --ds to change the "
            "number of sampling points."
        ),
        "group": "Defocus",
    },
]

LAMBDA_PARAM = Annotated[
    float | None,
    {
        "label": "Defocus regularisation lambda",
        "tooltip": (
            "Apply defocus regularisation if given. High-tilt images do not offer "
            "enough signal to recover the defocus value precisely. The regularisation "
            "forces the estimated defoci to assume similar values within a given tilt "
            "series, which prevents those high-tilt images from overfitting.\n"
            "This parameter gives the defocus regularisation scale. Larger values "
            "imply stronger regularisation."
        ),
        "group": "Defocus",
    },
]
DO_SCALE = Annotated[
    bool,
    {
        "label": "Refine contrast scale",
        "tooltip": "If enabled, then estimate the signal scale or ice thickness.",
        "group": "Defocus",
    },
]
DO_FRAME_SCALE = Annotated[
    bool,
    {
        "label": "Refine scale per frame",
        "tooltip": (
            "If enabled, then estimate the signal-scale parameter independently for "
            "each tilt. If not specified, the ice thickness, beam luminance and surface "
            "normal are estimated instead. Those three parameters then imply the signal "
            "intensity for each frame. Due to the smaller number of parameters, the ice "
            "thickness model is more robust to noise. By default, the ice thickness and "
            "surface normal will be estimated per tilt-series, and the beam luminance "
            "globally."
        ),
        "group": "Defocus",
    },
]
DO_TOMO_SCALE = Annotated[
    bool,
    {
        "label": "Refine scale per tomogram",
        "tooltip": (
            "If enabled, then estimate the beam luminance separately for each tilt "
            "series. This is not recommended."
        ),
        "group": "Defocus",
    },
]
