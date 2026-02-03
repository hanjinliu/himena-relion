from typing import Annotated

DO_HELIX = Annotated[
    bool,
    {
        "label": "Do helical reconstruction",
        "tooltip": "Perform 3D helical reconstruction.",
        "group": "Helix",
    },
]
HELICAL_TUBE_DIAMETER = Annotated[
    float,
    {
        "label": "Tube diameter (A)",
        "tooltip": (
            "Outer diameter (in Angstroms) of helical tubes. This value should be "
            "slightly larger than the actual width of the tubes."
        ),
        "group": "Helix",
    },
]
HELICAL_TUBE_DIAMETER_RANGE = Annotated[
    tuple[float, float],
    {
        "label": "Inner/Outer tube diameter (A)",
        "tooltip": (
            "Inner and outer diameter (in Angstroms) of the reconstructed helix "
            "spanning across Z axis. Set the inner diameter to negative value if the "
            "helix is not hollow in the center. The outer diameter should be slightly "
            "larger than the actual width of helical tubes because it also decides "
            "the shape of 2D particle mask for each segment. If the psi priors of the "
            "extracted segments are not accurate enough due to high noise level or "
            "flexibility of the structure, then set the outer diameter to a large "
            "value."
        ),
        "group": "Helix",
    },
]
ROT_TILT_PSI_RANGE = Annotated[
    tuple[float, float, float],
    {
        "label": "Angular search ranges (rot, tilt, psi) (deg)",
        "tooltip": (
            "Local angular searches will be performed within +/- of the given amount "
            "(in degrees) from the optimal orientation in the previous iteration. The "
            "default negative value means that no local searches will be performed. A "
            "Gaussian prior will be applied, so that orientations closer to the "
            "optimal orientation in the previous iteration will get higher weights "
            "than those further away.\n\nThese ranges will only be applied to the "
            "rot, tilt and psi angles in the first few iterations (global searches "
            "for orientations) in 3D helical reconstruction. Values of 9 or 15 "
            "degrees are commonly used. Higher values are recommended for more "
            "flexible structures and more memory and computation time will be used. "
            "A range of 15 degrees means sigma = 5 degrees.\n\nThese options will be "
            "invalid if you choose to perform local angular searches or not to "
            "perform image alignment on 'Sampling' tab."
        ),
        "group": "Helix",
    },
]
DO_APPLY_HELICAL_SYMMETRY = Annotated[
    bool,
    {
        "label": "Apply helical symmetry",
        "tooltip": (
            "If set to Yes, helical symmetry will be applied in every iteration. Set "
            "to No if you have just started a project, helical symmetry is unknown or "
            "not yet estimated."
        ),
        "group": "Helix",
    },
]
DO_LOCAL_SEARCH_H_SYM = Annotated[
    bool,
    {
        "label": "Do local searches of symmetry",
        "tooltip": (
            "If set to Yes, then perform local searches of helical twist and rise "
            "within given ranges."
        ),
        "group": "Helix",
    },
]
HELICAL_RANGE_DIST = Annotated[
    float,
    {
        "label": "Range factor of local averaging",
        "tooltip": (
            "Local averaging of orientations and translations will be performed "
            "within a range of +/- this value * the box size. Polarities are also set "
            "to be the same for segments coming from the same tube during local "
            "refinement. Values of ~ 2.0 are recommended for flexible structures such "
            "as MAVS-CARD filaments, ParM, MamK, etc. This option might not improve "
            "the reconstructions of helices formed from curled 2D lattices (TMV and "
            "VipA/VipB). Set to negative to disable this option."
        ),
        "group": "Helix",
    },
]
HELICAL_TWIST = Annotated[
    float,
    {
        "label": "Helical twist (deg)",
        "tooltip": (
            "Set helical twist (in degrees) to positive value if it is a right-handed "
            "helix. Helical rise is a positive value in Angstroms."
        ),
        "group": "Helix",
    },
]
HELICAL_TWIST_INITIAL = Annotated[
    float,
    {
        "label": "Initial helical twist (deg)",
        "tooltip": (
            "Initial helical symmetry. Set helical twist (in degrees) to positive "
            "value if it is a right-handed helix. If local searches of helical "
            "symmetry are planned, initial values of helical twist and rise should be "
            "within their respective ranges."
        ),
        "group": "Helix",
    },
]
HELICAL_TWIST_RANGE = Annotated[
    tuple[float, float, float],
    {
        "label": "Helical twist min/max/step (deg)",
        "tooltip": (
            "Minimum, maximum and initial step for helical twist search. Set helical "
            "twist (in degrees) to positive value if it is a right-handed helix. "
            "Generally it is not necessary for the user to provide an initial step "
            "(less than 1 degree, 5~1000 samplings as default). But it needs to be "
            "set manually if the default value does not guarantee convergence. The "
            "program cannot find a reasonable symmetry if the true helical "
            "parameters fall out of the given ranges. Note that the final "
            "reconstruction can still converge if wrong helical and point group "
            "symmetry are provided."
        ),
        "group": "Helix",
    },
]
HELICAL_RISE = Annotated[
    float,
    {
        "label": "Helical rise (A)",
        "tooltip": "Helical rise in Angstroms.",
        "group": "Helix",
    },
]
HELICAL_RISE_INITIAL = Annotated[
    float,
    {
        "label": "Initial helical rise (A)",
        "tooltip": (
            "Initial helical symmetry. Helical rise is a positive value in Angstroms. "
            "If local searches of helical symmetry are planned, initial values of "
            "helical twist and rise should be within their respective ranges."
        ),
        "group": "Helix",
    },
]
HELICAL_RISE_RANGE = Annotated[
    tuple[float, float, float],
    {
        "label": "Helical rise min/max/step (A)",
        "tooltip": (
            "Minimum, maximum and initial step for helical rise search. Helical rise "
            "is a positive value in Angstroms. Generally it is not necessary for the "
            "user to provide an initial step (less than 1% the initial helical rise, "
            "5~1000 samplings as default). But it needs to be set manually if the "
            "default value does not guarantee convergence. The program cannot find "
            "a reasonable symmetry if the true helical parameters fall out of the "
            "given ranges. Note that the final reconstruction can still converge if "
            "wrong helical and point group symmetry are provided."
        ),
        "group": "Helix",
    },
]
HELICAL_NR_ASU = Annotated[
    int,
    {
        "label": "Number of asymmetrical units",
        "tooltip": (
            "Number of unique helical asymmetrical units in each segment box. If the "
            "inter-box distance (set in segment picking step) is 100 Angstroms and "
            "the estimated helical rise is ~20 Angstroms, then set this value to "
            "100 / 20 = 5 (nearest integer). This integer should not be less than 1. "
            "The correct value is essential in measuring the signal to noise ratio "
            "in helical reconstruction."
        ),
        "group": "Helix",
    },
]
HELICAL_Z_PERCENTAGE = Annotated[
    float,
    {
        "label": "Central Z length (%)",
        "tooltip": (
            "Reconstructed helix suffers from inaccuracies of orientation searches. "
            "The central part of the box contains more reliable information compared "
            "to the top and bottom parts along Z axis, where Fourier artefacts are "
            "also present if the number of helical asymmetrical units is larger than "
            "1. Therefore, information from the central part of the box is used for "
            "searching and imposing helical symmetry in real space. Set this value "
            "(%) to the central part length along Z axis divided by the box size. "
            "Values around 30% are commonly used."
        ),
        "group": "Helix",
    },
]

KEEP_TILT_PRIOR_FIXED = Annotated[
    bool,
    {
        "label": "Keep tilt-prior fixed",
        "tooltip": (
            "If set to yes, the tilt prior will not change during the optimisation. "
            "If set to No, at each iteration the tilt prior will move to the optimal "
            "tilt value for that segment from the previous iteration."
        ),
        "group": "Helix",
    },
]
