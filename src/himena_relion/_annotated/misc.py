from typing import Annotated
from himena_relion._widgets._magicgui import BfactorEdit


TAU_FUDGE = Annotated[
    float,
    {
        "label": "Regularisation parameter T",
        "min": 0.1,
        "tooltip": (
            "Bayes law strictly determines the relative weight between the "
            "contribution of the experimental data and the prior. However, in "
            "practice one may need to adjust this weight to put slightly more weight "
            "on the experimental data to allow optimal results. Values greater than 1 "
            "for this regularisation parameter (T in the JMB2011 paper) put more "
            "weight on the experimental data. Values around 2-4 have been observed to "
            "be useful for 3D refinements, values of 1-2 for 2D refinements. "
            "Too small values yield too-low resolution structures; too high values "
            "result in over-estimated resolutions, mostly notable by the apparition "
            "of high-frequency noise in the references."
        ),
        "group": "Optimisation",
    },
]
CONTINUE_MANUALLY = Annotated[
    bool,
    {
        "label": "Continue manually",
        "tooltip": (
            "If set to Yes, an Autopick job can be continued as a manualpick job, so "
            "that incorrect picks can be corrected interactively."
        ),
        "group": "Picking",
    },
]
TRUST_REF_SIZE = Annotated[
    bool,
    {
        "label": "Resize reference if needed",
        "tooltip": (
            "If true, and if the input reference map (and mask) do not have the same "
            "pixel size and/or box size, then they will be re-scaled and re-boxed "
            "accordingly. If this option is set to false, then the program will die "
            "with an error if the reference does not have the correct pixel and/or box "
            "size."
        ),
        "group": "Reference",
    },
]
REF_CORRECT_GRAY = Annotated[
    bool,
    {
        "label": "Reference is on absolute grayscale",
        "tooltip": (
            "Probabilities are calculated based on a Gaussian noise model, which "
            "contains a squared difference term between the reference and the "
            "experimental image. This has a consequence that the reference needs to be "
            "on the same absolute intensity grey-scale as the experimental images. "
            "RELION and XMIPP reconstruct maps at their absolute intensity grey-scale. "
            "Other packages may perform internal normalisations of the reference "
            "density, which will result in incorrect grey-scales. Therefore: if the "
            "map was reconstructed in RELION or in XMIPP, set this option to Yes, "
            "otherwise set it to No. If set to No, RELION will use a (grey-scale "
            "invariant) cross-correlation criterion in the first iteration, and prior "
            "to the second iteration the map will be filtered again using the initial "
            "low-pass filter. This procedure is relatively quick and typically does "
            "not negatively affect the outcome of the subsequent MAP refinement. "
            "Therefore, if in doubt it is recommended to set this option to No."
        ),
        "group": "Reference",
    },
]

DO_BLUSH = Annotated[
    bool,
    {
        "label": "Use Blush regularisation",
        "tooltip": (
            "If set to Yes, relion_refine will use a neural network to perform "
            "regularisation by denoising at every iteration, instead of the standard "
            "smoothness regularisation."
        ),
        "group": "Optimisation",
    },
]

MASK_DIAMETER = Annotated[
    float,
    {
        "label": "Mask diameter (A)",
        "tooltip": (
            "The experimental images will be masked with a soft circular mask with "
            "this diameter. Make sure this radius is not set too small because that "
            "may mask away part of the signal! If set to a value larger than the image "
            "size no masking will be performed.\n\nThe same diameter will also be used "
            "for a spherical mask of the reference structures if no user-provided mask "
            "is specified."
        ),
        "group": "Optimisation",
    },
]


MASK_WITH_ZEROS = Annotated[
    bool,
    {
        "label": "Mask individual particles with zeros",
        "tooltip": (
            "If set to Yes, then in the individual particles, the area outside a "
            "circle with the radius of the particle will be set to zeros prior to "
            "taking the Fourier transform. This will remove noise and therefore "
            "increase sensitivity in the alignment and classification. However, it "
            "will also introduce correlations between the Fourier components that are "
            "not modelled. When set to No, then the solvent area is filled with "
            "random noise, which prevents introducing correlations. High-resolution "
            "refinements (e.g. ribosomes or other large complexes in 3D auto-refine) "
            "tend to work better when filling the solvent area with random noise (i.e. "
            "setting this option to No), refinements of smaller complexes and most "
            "classifications go better when using zeros (i.e. setting this option to "
            "Yes)."
        ),
        "group": "Optimisation",
    },
]
INITIAL_LOWPASS = Annotated[
    float,
    {
        "label": "Initial low-pass filter (A)",
        "tooltip": (
            "It is recommended to strongly low-pass filter your initial reference map. "
            "If it has not yet been low-pass filtered, it may be done internally using "
            "this option. If set to 0, no low-pass filter will be applied to the "
            "initial reference(s)."
        ),
        "group": "Reference",
    },
]
SOLVENT_FLATTEN_FSC = Annotated[
    bool,
    {
        "label": "Use solvent-flattened FSCs",
        "tooltip": (
            "If set to Yes, then instead of using unmasked maps to calculate the "
            "gold-standard FSCs during refinement, masked half-maps are used and a "
            "post-processing-like correction of the FSC curves (with "
            "phase-randomisation) is performed every iteration. This only works when a "
            "reference mask is provided on the I/O tab. This may yield "
            "higher-resolution maps, especially when the mask contains only a "
            "relatively small volume inside the box."
        ),
        "group": "Optimisation",
    },
]

DO_CTF = Annotated[
    bool,
    {
        "label": "Do CTF correction",
        "tooltip": (
            "If set to Yes, CTFs will be corrected inside the MAP refinement. The "
            "resulting algorithm intrinsically implements the optimal linear, or "
            "Wiener filter. Note that CTF parameters for all images need to be given "
            "in the input STAR file. The command 'relion_refine "
            "--print_metadata_labels' will print a list of all possible metadata "
            "labels for that STAR file. See the RELION Wiki for more details.\n\n "
            "Also make sure that the correct pixel size (in Angstrom) is given above!)"
        ),
        "group": "CTF",
    },
]
IGNORE_CTF = Annotated[
    bool,
    {
        "label": "Ignore CTFs until first peak",
        "tooltip": (
            "If set to Yes, then CTF-amplitude correction will only be performed from "
            "the first peak of each CTF onward. This can be useful if the CTF model "
            "is inadequate at the lowest resolution. Still, in general using higher "
            "amplitude contrast on the CTFs (e.g. 10-20%) often yields better results. "
            "Therefore, this option is not generally recommended: try increasing "
            "amplitude contrast (in your input STAR file) first!"
        ),
        "group": "CTF",
    },
]
REF_SYMMETRY = Annotated[
    str,
    {
        "label": "Symmetry",
        "tooltip": (
            "If the molecule is asymmetric, set Symmetry group to C1. Note their are "
            "multiple possibilities for icosahedral symmetry: \n"
            "* I1: No-Crowther 222 (standard in Heymann, Chagoyen & Belnap, JSB, 151 "
            "(2005) 196-207) \n "
            "* I2: Crowther 222 \n "
            "* I3: 52-setting (as used in SPIDER?)\n "
            "* I4: A different 52 setting \n "
            "The command <code>relion_refine --sym D2 --print_symmetry_ops</code> prints a list "
            "of all symmetry operators for symmetry group D2. RELION uses XMIPP's "
            "libraries for symmetry operations. Therefore, look at the "
            "<a href='https://i2pc.github.io/docs/Utils/Conventions/index.html#symmetry'>XMIPP documentation</a> for "
            "more details: "
        ),
        "group": "Reference",
    },
]
B_FACTOR = Annotated[
    dict,
    {
        "label": "B-factor",
        "widget_type": BfactorEdit,
        "tooltip": "B-factor",
        "group": "Sharpen",
    },
]
