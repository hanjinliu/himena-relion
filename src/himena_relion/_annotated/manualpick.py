from typing import Annotated, Union

DO_STARTEND = Annotated[
    bool,
    {
        "label": "Pick star-end coordinates helices",
        "tooltip": (
            "If set to true, start and end coordinates are picked subsequently and a "
            "line will be drawn between each pair"
        ),
        "group": "I/O",
    },
]
MINIMUM_PICK_FOM = Annotated[
    Union[float, None],
    {
        "label": "Minimum autopick FOM",
        "min": -10,
        "max": 10,
        "tooltip": (
            "The minimum value for the rlnAutopickFigureOfMerit for particles to be "
            "extracted."
        ),
        "group": "I/O",
    },
]
# Display
DIAMETER = Annotated[
    float,
    {
        "label": "Particle diameter (A)",
        "tooltip": (
            "The diameter of the circle used around picked particles (in Angstroms). "
            "Only used for display."
        ),
        "group": "Display",
    },
]
MICSCALE = Annotated[
    float,
    {
        "label": "Scale for micrographs",
        "tooltip": (
            "The micrographs will be displayed at this relative scale, i.e. a value of "
            "0.5 means that only every second pixel will be displayed."
        ),
        "group": "Display",
    },
]
SIGMA_CONTRAST = Annotated[
    float,
    {
        "label": "Sigma contrast",
        "tooltip": (
            "The micrographs will be displayed with the black value set to the average "
            "of all values MINUS this values times the standard deviation of all "
            "values in the micrograph, and the white value will be set to the average "
            "PLUS this value times the standard deviation. Use zero to set the minimum "
            "value in the micrograph to black, and the maximum value to white "
        ),
        "group": "Display",
    },
]
WHITE_VAL = Annotated[
    float,
    {
        "label": "White value",
        "tooltip": (
            "Use non-zero values to set the value of the whitest pixel in the "
            "micrograph."
        ),
        "group": "Display",
    },
]
BLACK_VAL = Annotated[
    float,
    {
        "label": "Black value",
        "tooltip": (
            "Use non-zero values to set the value of the blackest pixel in the "
            "micrograph."
        ),
        "group": "Display",
    },
]
ANGPIX = Annotated[
    float,
    {
        "label": "Pixel size (A)",
        "tooltip": (
            "Pixel size in Angstroms. This will be used to calculate the filters and "
            "the particle diameter in pixels. If a CTF-containing STAR file is input, "
            "then the value given here will be ignored, and the pixel size will be "
            "calculated from the values in the STAR file. A negative value can then be "
            "given here."
        ),
        "group": "Display",
    },
]
FILTER_METHOD = Annotated[
    str,
    {
        "label": "Denoising method",
        "choices": ["Band-pass", "Topaz"],
        "tooltip": (
            "Method used to denoise the micrographs for display purposes. 'Band-pass' "
            "will apply a simple band-pass filter, whereas 'Topaz' will use a "
            "pre-trained deep-learning model to denoise the micrographs."
        ),
        "group": "Display",
    },
]
LOWPASS = Annotated[
    float,
    {
        "label": "Lowpass filter (A)",
        "tooltip": (
            "Lowpass filter that will be applied to the micrographs. Give a negative "
            "value to skip the lowpass filter."
        ),
        "group": "Display",
    },
]
HIGHPASS = Annotated[
    float,
    {
        "label": "Highpass filter (A)",
        "tooltip": (
            "Highpass filter that will be applied to the micrographs. This may be "
            "useful to get rid of background ramps due to uneven ice distributions. "
            "Give a negative value to skip the highpass filter. Useful values are "
            "often in the range of 200-400 Angstroms."
        ),
        "group": "Display",
    },
]
# Colors
DO_COLOR = Annotated[
    bool,
    {
        "label": "Color particles by metadata",
        "tooltip": (
            "If set to true, then the circles for each particles are coloured from red "
            "to blue (or the other way around) for a given metadatalabel. If this "
            "metadatalabel is not in the picked coordinates STAR file (basically only "
            "the rlnAutopickFigureOfMerit or rlnClassNumber) would be useful values "
            "there, then you may provide an additional STAR file (e.g. after "
            "classification/refinement below. Particles with values -999, or that are "
            "not in the additional STAR file will be coloured the default color: green"
        ),
        "group": "Colors",
    },
]
COLOR_LABEL = Annotated[
    str,
    {
        "label": "Color by this label",
        "tooltip": (
            "The Metadata label of the value to plot from red to blue. Useful examples "
            "might be:\nrlnParticleSelectZScore \nrlnClassNumber "
            "\nrlnAutopickFigureOfMerit \n rlnAngleTilt \n rlnLogLikeliContribution "
            "\n rlnMaxValueProbDistribution \n rlnNrOfSignificantSamples\n"
        ),
        "group": "Colors",
    },
]
FN_COLOR = Annotated[
    str,
    {
        "label": "STAR file with color label",
        "tooltip": (
            "The program will figure out which particles in this STAR file are on the "
            "current micrograph and color their circles according to the value in the "
            "corresponding column. Particles that are not in this STAR file, but "
            "present in the picked coordinates file will be colored green. If this "
            "field is left empty, then the color label (e.g. rlnAutopickFigureOfMerit) "
            "should be present in the coordinates STAR file."
        ),
        "group": "Colors",
    },
]
BLUE_VALUE = Annotated[
    float,
    {
        "label": "Blue value",
        "tooltip": (
            "The value of this entry will be blue. There will be a linear scale from "
            "blue to red, according to this value and the one given below."
        ),
        "group": "Colors",
    },
]
RED_VALUE = Annotated[
    float,
    {
        "label": "Red value",
        "tooltip": (
            "The value of this entry will be red. There will be a linear scale from "
            "blue to red, according to this value and the one given above."
        ),
        "group": "Colors",
    },
]

# Tomogram

PICK_MODE = Annotated[
    str,
    {
        "label": "Picking mode",
        "choices": ["particles", "spheres", "surfaces", "filaments"],
        "tooltip": "Type of picking mode to use",
        "group": "I/O",
    },
]
PARTICLE_SPACING = Annotated[
    float,
    {
        "label": "Particle spacing (A)",
        "tooltip": (
            "Spacing (in Angstroms) between particles sampled on a sphere, on "
            "surfaces, or in filaments. This option will be ignored if you are picking "
            "individual particles"
        ),
        "group": "I/O",
    },
]
