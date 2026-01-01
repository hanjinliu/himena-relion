from pathlib import Path
from typing import Annotated

from himena_relion._widgets._path_input import PathDrop

ANGPIX = Annotated[
    float,
    {
        "label": "Micrograph pixel size (A)",
        "tooltip": (
            "Pixel size in Angstroms. If a CTF-containing STAR file is input, then the "
            "value given here will be ignored, and the pixel size will be calculated "
            "from the values in the STAR file. A negative value can then be given here."
        ),
        "group": "IO",
    },
]
# Laplacian
LOG_DIAM_MIN = Annotated[
    float,
    {
        "label": "Min diameter for LoG filter (A)",
        "tooltip": (
            "The smallest allowed diameter for the blob-detection algorithm. This "
            "should correspond to the smallest size of your particles in Angstroms."
        ),
        "group": "Laplacian",
    },
]
LOG_DIAM_MAX = Annotated[
    float,
    {
        "label": "Max diameter for LoG filter (A)",
        "tooltip": (
            "The largest allowed diameter for the blob-detection algorithm. This "
            "should correspond to the largest size of your particles in Angstroms."
        ),
        "group": "Laplacian",
    },
]
LOG_INVERT = Annotated[
    bool,
    {
        "label": "Dark background",
        "tooltip": (
            "Set this option to No if the particles are black, and to Yes if the "
            "particles are white."
        ),
        "group": "Laplacian",
    },
]
LOG_MAXRES = Annotated[
    float,
    {
        "label": "Max resolution to consider (A)",
        "tooltip": (
            "The Laplacian-of-Gaussian filter will be applied to downscaled "
            "micrographs with the corresponding size. Give a negative value to skip "
            "downscaling."
        ),
        "group": "Laplacian",
    },
]
LOG_ADJUST_THR = Annotated[
    float,
    {
        "label": "Adjust default threshold (stddev)",
        "tooltip": (
            "Use this to pick more (negative number -> lower threshold) or less "
            "(positive number -> higher threshold) particles compared to the default "
            "setting. The threshold is moved this many standard deviations away from "
            "the average."
        ),
        "group": "Laplacian",
    },
]

LOG_UPPER_THR = Annotated[
    float,
    {
        "label": "Upper threshold (stddev)",
        "tooltip": (
            "Use this to discard picks with LoG thresholds that are this many standard "
            "deviations above the average, e.g. to avoid high contrast contamination "
            "like ice and ethane droplets. Good values depend on the contrast of "
            "micrographs and need to be interactively explored; for low contrast "
            "micrographs, values of ~ 1.5 may be reasonable, but the same value will "
            "be too low for high-contrast micrographs."
        ),
        "group": "Laplacian",
    },
]
# Autopicking
THRESHOLD_AUTOPICK = Annotated[
    float,
    {
        "label": "Picking threshold",
        "tooltip": (
            "Use lower thresholds to pick more particles (and more junk probably)."
        ),
        "group": "Autopicking",
    },
]
MINDIST_AUTOPICK = Annotated[
    float,
    {
        "label": "Min inter-particle distance (A)",
        "tooltip": (
            "Particles closer together than this distance will be consider to be a "
            "single cluster. From each cluster, only one particle will be picked. \n\n"
            "This option takes no effect for picking helical segments. The inter-box "
            "distance is calculated with the number of asymmetrical units and the "
            "helical rise on 'Helix' tab."
        ),
        "group": "Autopicking",
    },
]
MAXSTDDEVNOISE_AUTOPICK = Annotated[
    float,
    {
        "label": "Max stddev noise",
        "tooltip": (
            "This is useful to prevent picking in carbon areas, or areas with big "
            "contamination features. Peaks in areas where the background standard "
            "deviation in the normalized micrographs is higher than this value will be "
            "ignored. Useful values are probably in the range 1.0 to 1.2. Set to -1 to "
            "switch off the feature to eliminate peaks due to high background standard "
            "deviations."
        ),
        "group": "Autopicking",
    },
]
DO_WHITE_FOM_MAPS = Annotated[
    bool,
    {
        "label": "Write FOM maps",
        "tooltip": (
            "If set to Yes, intermediate probability maps will be written out, which "
            "(upon reading them back in) will speed up tremendously the optimization "
            "of the threshold and inter-particle distance parameters. However, with "
            "this option, one cannot run in parallel, as disc I/O is very heavy with "
            "this option set."
        ),
        "group": "Autopicking",
    },
]
DO_READ_FOM_MAPS = Annotated[
    bool,
    {
        "label": "Read FOM maps",
        "tooltip": (
            "If written out previously, read the FOM maps back in and re-run the "
            "picking to quickly find the optimal threshold and inter-particle distance "
            "parameters"
        ),
        "group": "Autopicking",
    },
]
SHRINK = Annotated[
    float,
    {
        "label": "Shrink factor",
        "tooltip": (
            "This is useful to speed up the calculations, and to make them less "
            "memory-intensive. The micrographs will be downscaled (shrunk) to "
            "calculate the cross-correlations, and peak searching will be done in the "
            "downscaled FOM maps. When set to 0, the micrographs will de downscaled to "
            "the lowpass filter of the references, a value between 0 and 1 will "
            "downscale the micrographs by that factor. Note that the results will not "
            "be exactly the same when you shrink micrographs!\n\nIn the "
            "Laplacian-of-Gaussian picker, this option is ignored and the shrink "
            "factor always becomes 0."
        ),
        "group": "Autopicking",
    },
]
# Helical
DO_PICK_HELICAL_SEGMENTS = Annotated[
    bool,
    {
        "label": "Pick 2D helical segments",
        "tooltip": (
            "Set to Yes if you want to pick 2D helical segments. Note this will run "
            "the old algorithms for reference-based helical segment picking, as "
            "described by He & Scheres, J Struct Biol, 2017. Often, we now run "
            "filament picking by Topaz instead...."
        ),
        "group": "Helix",
    },
]
HELICAL_TUBE_LENGTH_MIN = Annotated[
    float,
    {
        "label": "Minimum length (A)",
        "tooltip": (
            "Minimum length (in Angstroms) of helical tubes for auto-picking. Helical "
            "tubes with shorter lengths will not be picked. Note that a long helical "
            "tube seen by human eye might be treated as short broken pieces due to low "
            "FOM values or high picking threshold."
        ),
        "group": "Helix",
    },
]
HELICAL_TUBE_KAPPA_MAX = Annotated[
    float,
    {
        "label": "Maximum curvature (kappa)",
        "tooltip": (
            "Maximum curvature allowed for picking helical tubes. Kappa = 0.3 means "
            "that the curvature of the picked helical tubes should not be larger than "
            "30% the curvature of a circle (diameter = particle mask diameter). Kappa "
            "~ 0.05 is recommended for long and straight tubes (e.g. TMV, VipA/VipB "
            "and AChR tubes) while 0.20 ~ 0.40 seems suitable for flexible ones (e.g. "
            "ParM and MAVS-CARD filaments)."
        ),
        "group": "Helix",
    },
]
DO_AMYLOID = Annotated[
    bool,
    {
        "label": "Pick amyloid segments",
        "tooltip": (
            "Set to Yes if you want to use the algorithm that was developed "
            "specifically for picking amyloids."
        ),
        "group": "Helix",
    },
]

FN_REFS_AUTOPICK = Annotated[
    str,
    {
        "label": "2D reference",
        "tooltip": (
            "Input STAR file or MRC stack with the 2D references to be used for "
            "picking. Note that the absolute greyscale needs to be correct, so <b>only "
            "use images created by RELION itself</b>, e.g. by 2D class averaging or "
            "projecting a RELION reconstruction."
        ),
        "group": "References",
    },
]
LOWPASS = Annotated[
    float,
    {
        "label": "Lowpass filter references",
        "tooltip": (
            "Lowpass filter that will be applied to the references before template "
            "matching. Do NOT use very high-resolution templates to search your "
            "micrographs. The signal will be too weak at high resolution anyway, and "
            "you may find Einstein from noise.... Give a negative value to skip the "
            "lowpass filter."
        ),
        "group": "References",
    },
]
HIGHPASS = Annotated[
    float,
    {
        "label": "Highpass filter micrographs",
        "tooltip": (
            "Highpass filter that will be applied to the micrographs. This may be "
            "useful to get rid of background ramps due to uneven ice distributions. "
            "Give a negative value to skip the highpass filter. Useful values are "
            "often in the range of 200-400 Angstroms."
        ),
        "group": "References",
    },
]
ANGPIX_REF = Annotated[
    float,
    {
        "label": "Reference pixel size",
        "tooltip": (
            "Pixel size in Angstroms for the provided reference images. This will be "
            "used to calculate the filters and the particle diameter in pixels. If a "
            "negative value is given here, the pixel size in the references will be "
            "assumed to be the same as the one in the micrographs, i.e. the particles "
            "that were used to make the references were not rescaled upon extraction."
        ),
        "group": "References",
    },
]
PSI_SAMPLING_AUTOPICK = Annotated[
    float,
    {
        "label": "In-plane angular sampling (deg)",
        "tooltip": (
            "Angular sampling in degrees for exhaustive searches of the in-plane "
            "rotations for all references."
        ),
        "group": "References",
    },
]
DO_INVERT_REFS = Annotated[
    bool,
    {
        "label": "References have inverted contrast",
        "tooltip": (
            "Set to Yes to indicate that the reference have inverted contrast with "
            "respect to the particles in the micrographs."
        ),
        "group": "References",
    },
]
DO_CTF_AUTOPICK = Annotated[
    bool,
    {
        "label": "References are CTF corrected",
        "tooltip": (
            "Set to Yes if the references were created with CTF-correction inside "
            "RELION.\n\nIf set to Yes, the input micrographs can only be given as a "
            "STAR file, which should contain the CTF information for each micrograph."
        ),
        "group": "References",
    },
]
DO_IGNORE_FIRST_CTFPEAK_AUTOPICK = Annotated[
    bool,
    {
        "label": "Ignore CTFs until first peak",
        "tooltip": (
            "Set this to Yes, only if this option was also used to generate the "
            "references."
        ),
        "group": "References",
    },
]
MINAVGNOISE_AUOTPICK = Annotated[
    float,
    {
        "label": "Min avg noise",
        "tooltip": (
            "This is useful to prevent picking in carbon areas, or areas with big "
            "contamination features. Peaks in areas where the background standard "
            "deviation in the normalized micrographs is higher than this value will be "
            "ignored. Useful values are probably in the range -0.5 to 0. Set to -999 "
            "to switch off the feature to eliminate peaks due to low average "
            "background densities."
        ),
        "group": "Autopicking",
    },
]
REF3D_SYMMETRY = Annotated[
    str,
    {
        "label": "Symmetry",
        "tooltip": (
            "Symmetry point group of the 3D reference. Only projections in the "
            "asymmetric part of the sphere will be generated."
        ),
        "group": "References",
    },
]
REF3D_SAMPLING = Annotated[
    str,
    {
        "label": "3D angular sampling",
        "tooltip": (
            "There are only a few discrete angular samplings possible because we use "
            "the HealPix library to generate the sampling of the first two Euler "
            "angles on the sphere. The samplings are approximate numbers and vary "
            "slightly over the sphere.\n\n For autopicking, 30 degrees is usually fine "
            "enough, but for highly symmetrical objects one may need to go finer to "
            "adequately sample the asymmetric part of the sphere."
        ),
        "choices": [
            "30 degrees",
            "15 degrees",
            "7.5 degrees",
            "3.7 degrees",
            "1.8 degrees",
            "0.9 degrees",
            "0.5 degrees",
            "0.2 degrees",
            "0.1 degrees",
        ],
        "group": "References",
    },
]

# Topaz
TOPAZ_PARTICLE_DIAMETER = Annotated[
    float,
    {
        "label": "Particle diameter (A)",
        "tooltip": (
            "Diameter of the particle (to be used to infer topaz downscale factor and "
            "particle radius)"
        ),
        "group": "Topaz",
    },
]
TOPAZ_NR_PARTICLES = Annotated[
    float,
    {
        "label": "Number of particles per micrographs",
        "tooltip": "Expected average number of particles per micrograph",
        "group": "Topaz",
    },
]
DO_TOPAZ_TRAIN_PARTS = Annotated[
    bool,
    {
        "label": "Train on a set of particles",
        "tooltip": (
            "If set to Yes, the input Coordinates above will be ignored. Instead, one "
            "uses a _data.star file from a previous 2D or 3D refinement or selection "
            "to use those particle positions for training."
        ),
        "group": "Topaz",
    },
]
TOPAZ_TRAIN_PICKS = Annotated[
    str,
    {
        "label": "Input picked coordinates for training",
        "tooltip": (
            "Input STAR file (preferably with CTF information) with all micrographs to "
            "pick from."
        ),
        "group": "Topaz",
    },
]
TOPAZ_TRAIN_PARTS = Annotated[
    str,
    {
        "label": "Particles STAR file for training",
        "tooltip": (
            "Filename of the STAR file with the particle coordinates to be used for "
            "training, e.g. from a previous 2D or 3D classification or selection."
        ),
        "widget_type": PathDrop,
        "type_label": "MicrographsCoords",
        "group": "Topaz",
    },
]
TOPAZ_MODEL = Annotated[
    Path,
    {
        "label": "Trained Topaz model",
        "tooltip": (
            "Trained topaz model for topaz-based picking. Use on job for training and "
            "a next job for picking. Leave this empty to use the default (general) model."
        ),
        "filter": "SAV Files (*.sav)",
        "group": "Topaz",
    },
]
DO_TOPAZ_FILAMENTS = Annotated[
    bool,
    {
        "label": "Pick filaments",
        "tooltip": (
            "If set to Yes, this option will activate the -f option in our modified "
            "version of topaz that can pick filaments, as described in "
            "Lovestam & Scheres, Faraday Discussions 2022",
        ),
        "group": "Topaz",
    },
]
TOPAZ_FILAMENT_THRESHOLD = Annotated[
    float,
    {
        "label": "Filament threshold",
        "tooltip": (
            "This sets the filament picking threshold and the length of the Hough "
            "transform, as described in Lovestam & Scheres, Faraday Discussions 2022. "
            "Useful values in our work on recombinant tau for the threshold range "
            "from -4 to -7. We typically do not change the default length of the Hough "
            "transform, which is set to be equal to the particle diameter when a "
            "negative value is given here. You can provide the additional option -fp "
            "to display images of intermediate steps of the algorithm to tune "
            "difficult cases."
        ),
        "group": "Topaz",
    },
]
TOPAZ_HOUGH_LENGTH = Annotated[
    float,
    {
        "label": "Hough length",
        "tooltip": (
            "This sets the filament picking threshold and the length of the Hough "
            "transform, as described in Lovestam & Scheres, Faraday Discussions 2022. "
            "Useful values in our work on recombinant tau for the threshold range from "
            "-4 to -7. We typically do not change the default length of the Hough "
            "transform, which is set to be equal to the particle diameter when a "
            "negative value is given here. You can provide the additional option -fp "
            "to display images of intermediate steps of the algorithm to tune "
            "difficult cases."
        ),
        "group": "Topaz",
    },
]
TOPAZ_OTHER_ARGS = Annotated[
    str,
    {
        "label": "Additional Topaz arguments",
        "tooltip": "These additional arguments will be passed onto all topaz programs.",
        "group": "Topaz",
    },
]
