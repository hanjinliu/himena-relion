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
            "If set to Yes, then relion_ctf_refine will also estimate the beamtilt per "
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
            "If set to Yes, then relion_ctf_refine will also estimate the trefoil "
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
            "If set to Yes, then relion_ctf_refine will also estimate the Cs and the "
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
