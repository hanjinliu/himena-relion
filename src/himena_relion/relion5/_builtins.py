from pathlib import Path
from typing import Annotated, Any, Literal

from magicgui.widgets.bases import ValueWidget
from himena_relion._job_class import _RelionBuiltinJob, parse_string
from himena_relion._job_dir import JobDirectory
from himena_relion._widgets._magicgui import PathDrop, BfactorEdit, Class2DAlgorithmEdit
from himena_relion import _configs
from himena_relion.schemas import OptimisationSetModel


# I/O
IN_MOVIES = Annotated[
    str,
    {
        "label": "Input movies",
        "widget_type": PathDrop,
        "type_label": "MicrographMoviesData",
        "group": "I/O",
    },
]
IN_MICROGRAPHS = Annotated[
    str,
    {
        "label": "Input micrographs",
        "widget_type": PathDrop,
        "type_label": ["MicrographsData", "MicrographGroupMetadata"],
        "group": "I/O",
    },
]
IN_COORDINATES = Annotated[
    str,
    {
        "label": "Input coordinates",
        "widget_type": PathDrop,
        "type_label": "MicrographsCoords",
        "group": "I/O",
    },
]
IN_PARTICLES = Annotated[
    str,
    {
        "label": "Input particles",
        "widget_type": PathDrop,
        "type_label": ["ParticlesData", "ParticleGroupMetadata"],
        "group": "I/O",
    },
]
IMG_TYPE = Annotated[
    str,
    {
        "label": "Input images",
        "widget_type": PathDrop,
        "type_label": "ParticlesData",
        "group": "I/O",
    },
]
REF_TYPE = Annotated[
    str,
    {
        "label": "Reference map",
        "widget_type": PathDrop,
        "type_label": "DensityMap",
        "group": "I/O",
    },
]
MAP_TYPE = Annotated[
    str,
    {
        "label": "Input 3D map",
        "widget_type": PathDrop,
        "type_label": "DensityMap",
        "group": "I/O",
    },
]
HALFMAP_TYPE = Annotated[
    str,
    {
        "label": "One of the half-maps",
        "widget_type": PathDrop,
        "type_label": "DensityMap",
        "group": "I/O",
    },
]
MASK_TYPE = Annotated[
    str,
    {
        "label": "Reference mask (optional)",
        "widget_type": PathDrop,
        "type_label": "Mask3D",
        "group": "I/O",
    },
]
PROCESS_TYPE = Annotated[
    str,
    {
        "label": "Input postprocess STAR",
        "widget_type": PathDrop,
        "type_label": "ProcessData",
        "group": "I/O",
    },
]
IN_OPTIMISER = Annotated[
    str,
    {
        "label": "Input optimiser STAR",
        "widget_type": PathDrop,
        "type_label": "OptimiserData",
        "group": "I/O",
    },
]
CONTINUE_TYPE = Annotated[
    str,
    {
        "label": "Continue from here",
        "widget_type": PathDrop,
        "type_label": "ProcessData",
        "group": "I/O",
    },
]
# Motion correction
MCOR_FIRST_FRAME_SUM_TYPE = Annotated[
    int, {"label": "First frame for corrected sum", "group": "I/O"}
]
MCOR_LAST_FRAME_SUM_TYPE = Annotated[
    int, {"label": "Last frame for corrected sum", "group": "I/O"}
]
MCOR_DOSE_PER_FRAME_TYPE = Annotated[
    float, {"label": "Dose per frame (e/A^2)", "group": "I/O"}
]
MCOR_PRE_EXPOSURE_TYPE = Annotated[
    float, {"label": "Pre-exposure (e/A^2)", "group": "I/O"}
]
MCOR_EER_FRAC_TYPE = Annotated[
    int, {"label": "EER fractionation", "min": 1, "group": "I/O"}
]
DO_F16_TYPE = Annotated[bool, {"label": "Write output in float16", "group": "I/O"}]
MCOR_DO_DOSE_WEIGHTING_TYPE = Annotated[
    bool, {"label": "Do dose-weighting", "group": "I/O"}
]
MCOR_DO_SAVE_NO_DW_TYPE = Annotated[
    bool, {"label": "Save non-dose weighted as well", "group": "I/O"}
]
MCOR_DO_SAVE_PS_TYPE = Annotated[
    bool, {"label": "Save sum of power spectra", "group": "I/O"}
]
MCOR_SUM_EVERY_E_TYPE = Annotated[
    float, {"label": "Sum power spectra every (e/A^2)", "group": "I/O"}
]
MCOR_BFACTOR_TYPE = Annotated[float, {"label": "Bfactor", "group": "Motion Correction"}]
MCOR_GROUP_FRAMES_TYPE = Annotated[
    int, {"label": "Group frames", "min": 1, "group": "Motion Correction"}
]
MCOR_BIN_FACTOR_TYPE = Annotated[
    int, {"label": "Binning factor", "min": 1, "group": "Motion Correction"}
]
MCOR_DEFECT_FILE_TYPE = Annotated[
    str, {"label": "Defect file", "group": "Motion Correction"}
]
MCOR_GAIN_REF_TYPE = Annotated[
    str, {"label": "Gain reference image", "group": "Motion Correction"}
]
MCOR_GAIN_ROT_TYPE = Annotated[
    str,
    {
        "choices": [
            "No rotation (0)",
            "90 degrees (1)",
            "180 degrees (2)",
            "270 degrees (3)",
        ],
        "label": "Gain reference flipping",
        "group": "Motion Correction",
    },
]
MCOR_GAIN_FLIP_TYPE = Annotated[
    str,
    {
        "choices": [
            "No flipping (0)",
            "Flip upside down (1)",
            "Flip left to right (2)",
        ],
        "label": "Gain reference flipping",
        "group": "Motion Correction",
    },
]
MCOR_PATCH_TYPE = Annotated[
    tuple[int, int],
    {"label": "Number of patches (X, Y)", "group": "Motion Correction"},
]
# CTF
DO_CTF_TYPE = Annotated[bool, {"label": "Do CTF correction", "group": "CTF"}]
IGNORE_CTF_TYPE = Annotated[
    bool, {"label": "Ignore CTFs until first peak", "group": "CTF"}
]
# Extract
EXTRACT_SIZE_TYPE = Annotated[
    int, {"label": "Particle box size (pix)", "group": "Extract"}
]
EXTRACT_RESCALE_TYPE = Annotated[
    int, {"label": "Rescaled box size (pix)", "group": "Extract"}
]
EXTRACT_INVERT_TYPE = Annotated[bool, {"label": "Invert contrast", "group": "Extract"}]
EXTRACT_NORM_TYPE = Annotated[
    bool, {"label": "Normalize particles", "group": "Extract"}
]
EXTRACT_DIAMETER_TYPE = Annotated[
    float, {"label": "Diameter of background circle (pix)", "group": "Extract"}
]
EXTRACT_WIGHT_DUST_TYPE = Annotated[
    float, {"label": "Stddev for white dust removal", "group": "Extract"}
]
EXTRACT_BLACK_DUST_TYPE = Annotated[
    float, {"label": "Stddev for black dust removal", "group": "Extract"}
]
# Reference
REF_SYMMETRY_TYPE = Annotated[str, {"label": "Symmetry", "group": "Reference"}]
REF_CORRECT_GRAY_TYPE = Annotated[
    bool, {"label": "Reference is on absolute grayscale", "group": "Reference"}
]
INITIAL_LOWPASS_TYPE = Annotated[
    float, {"label": "Initial low-pass filter (A)", "group": "Reference"}
]
TRUST_REF_SIZE_TYPE = Annotated[
    bool, {"label": "Resize reference if needed", "group": "Reference"}
]
# Optimisation
T_TYPE = Annotated[
    float, {"label": "Regularisation parameter T", "min": 0.1, "group": "Optimisation"}
]
NUM_ITER_TYPE = Annotated[
    int, {"label": "Number of iterations", "min": 1, "group": "Optimisation"}
]
NUM_CLASS_TYPE = Annotated[
    int, {"label": "Number of classes", "min": 1, "group": "Optimisation"}
]
MASK_DIAMETER_TYPE = Annotated[
    float, {"label": "Mask diameter (A)", "group": "Optimisation"}
]
MASK_WITH_ZEROS_TYPE = Annotated[
    bool, {"label": "Mask individual particles with zeros", "group": "Optimisation"}
]
SOLVENT_FLATTEN_FSC_TYPE = Annotated[
    bool, {"label": "Use solvent-flattened FSCs", "group": "Optimisation"}
]
DO_BLUSH_TYPE = Annotated[
    bool, {"label": "Use Blush regularisation", "group": "Optimisation"}
]
# Sampling
DONT_SKIP_ALIGN_TYPE = Annotated[
    bool, {"label": "Perform image alignment", "group": "Sampling"}
]
SIGMA_TILT_TYPE = Annotated[
    float, {"label": "Prior width on tilt angle", "group": "Sampling"}
]
ALLOW_COARSER_SAMPLING_TYPE = Annotated[
    bool, {"label": "Allow coarser sampling", "group": "Sampling"}
]
ANG_SAMPLING_TYPE = Annotated[
    str,
    {
        "label": "Angular sampling interval",
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
        "group": "Sampling",
    },
]
OFFSET_RANGE_STEP_TYPE = Annotated[
    tuple[float, float],
    {"label": "Offset search range/step (pix)", "group": "Sampling"},
]
RELAX_SYMMETRY_TYPE = Annotated[str, {"label": "Relax symmetry", "group": "Sampling"}]
KEEP_TILT_PRIOR_FIXED_TYPE = Annotated[
    bool, {"label": "Keep tilt-prior fixed", "group": "Helix"}
]
LOC_ANG_SAMPLING_TYPE = Annotated[
    str,
    {
        "label": "Local angular sampling interval",
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
        "group": "Sampling",
    },
]
# Helix
DO_HELIX_TYPE = Annotated[
    bool, {"label": "Do helical reconstruction", "group": "Helix"}
]
HELICAL_TUBE_DIAMETER_TYPE = Annotated[
    float, {"label": "Tube diameter (A)", "group": "Helix"}
]
HELICAL_TUBE_DIAMETER_RANGE_TYPE = Annotated[
    tuple[float, float],
    {"label": "Inner/Outer tube diameter (A)", "group": "Helix"},
]
ROT_TILT_PSI_RANGE_TYPE = Annotated[
    tuple[float, float, float],
    {"label": "Angular search ranges (rot, tilt, psi) (deg)", "group": "Helix"},
]
DO_APPLY_HELICAL_SYMMETRY_TYPE = Annotated[
    bool, {"label": "Apply helical symmetry", "group": "Helix"}
]
DO_LOCAL_SEARCH_HELICAL_SYMMETRY_TYPE = Annotated[
    bool, {"label": "Do local searches of symmetry", "group": "Helix"}
]
HELICAL_RANGE_DIST_TYPE = Annotated[
    float, {"label": "Range factor of local averaging", "group": "Helix"}
]
HELICAL_TWIST_INITIAL_TYPE = Annotated[
    float, {"label": "Initial helical twist (deg)", "group": "Helix"}
]
HELICAL_TWIST_RANGE_TYPE = Annotated[
    tuple[float, float, float],
    {"label": "Helical twist min/max/step (deg)", "group": "Helix"},
]
HELICAL_RISE_TYPE = Annotated[float, {"label": "Helical rise (A)", "group": "Helix"}]
HELICAL_RISE_INITIAL_TYPE = Annotated[
    float, {"label": "Initial helical rise (A)", "group": "Helix"}
]
HELICAL_RISE_RANGE_TYPE = Annotated[
    tuple[float, float, float],
    {"label": "Helical rise min/max/step (A)", "group": "Helix"},
]
HELICAL_NR_ASU_TYPE = Annotated[
    int, {"label": "Number of asymmetrical units", "group": "Helix"}
]
HELICAL_Z_PERCENTAGE_TYPE = Annotated[
    float, {"label": "Central Z length (%)", "group": "Helix"}
]

# Compute
USE_PARALLEL_DISC_IO_TYPE = Annotated[
    bool, {"label": "Use parallel disc I/O", "group": "Compute"}
]
NUM_POOL_TYPE = Annotated[
    int, {"label": "Number of pooled particles", "min": 1, "group": "Compute"}
]
DO_PREREAD_TYPE = Annotated[
    bool, {"label": "Pre-read all particles into RAM", "group": "Compute"}
]
USE_SCRATCH_TYPE = Annotated[
    bool,
    {
        "label": "Copy particles to scratch directory",
        "tooltip": "Preload particles to scratch directory to improve I/O performance during computation.",
        "group": "Compute",
    },
]
DO_COMBINE_THRU_DISC_TYPE = Annotated[
    bool, {"label": "Combine iterations through disc", "group": "Compute"}
]
GPU_IDS_TYPE = Annotated[str, {"label": "GPU IDs to use", "group": "Compute"}]
USE_FAST_SUBSET_TYPE = Annotated[
    bool, {"label": "Use fast subsets", "group": "Compute"}
]
# class 3d
LOCAL_ANG_SEARCH_TYPE = Annotated[
    bool, {"label": "Perform local angular searches", "group": "Sampling"}
]
HIGH_RES_LIMIT_TYPE = Annotated[
    float, {"label": "High-resolution limit (A)", "group": "Optimisation"}
]
# sharpen
B_FACTOR_TYPE = Annotated[
    dict,
    {
        "label": "B-factor",
        "widget_type": BfactorEdit,
        "group": "Sharpen",
    },
]
# running
MPI_TYPE = Annotated[
    int,
    {"label": "Number of MPI processes", "min": 1, "max": 64, "group": "Running"},
]
THREAD_TYPE = Annotated[
    int,
    {"label": "Number of threads", "min": 1, "max": 64, "group": "Running"},
]
DO_QUEUE_TYPE = Annotated[
    bool,
    {"label": "Submit to queue", "group": "Running"},
]
MIN_DEDICATED_TYPE = Annotated[
    int,
    {
        "label": "Minimum dedicated cores per node",
        "min": 1,
        "max": 64,
        "group": "Running",
    },
]


class _Relion5Job(_RelionBuiltinJob):
    @classmethod
    def command_palette_title_prefix(cls):
        return "RELION 5:"


class _MotionCorrJobBase(_Relion5Job):
    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_motioncor2_exe"] = _configs.get_motioncor2_exe()
        if "patch" in kwargs:
            kwargs["patch_x"], kwargs["patch_y"] = kwargs.pop("patch")
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("fn_motioncor2_exe", None)
        kwargs["patch"] = (kwargs.pop("patch_x", 1), kwargs.pop("patch_y", 1))
        return super().normalize_kwargs_inv(**kwargs)


class MotionCorr2Job(_MotionCorrJobBase):
    """Motion correction using MotionCor2 (GPU)."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.motioncorr.motioncor2"

    @classmethod
    def job_title(cls):
        return "Motion Correction (MotionCor2)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_own_motioncor"] = False
        kwargs["do_save_ps"] = False
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("do_own_motioncor", None)
        kwargs.pop("do_save_ps", None)
        return kwargs

    def run(
        self,
        input_star_mics: IN_MOVIES = "",
        first_frame_sum: MCOR_FIRST_FRAME_SUM_TYPE = 1,
        last_frame_sum: MCOR_LAST_FRAME_SUM_TYPE = -1,
        dose_per_frame: MCOR_DOSE_PER_FRAME_TYPE = 1.0,
        pre_exposure: MCOR_PRE_EXPOSURE_TYPE = 0.0,
        eer_grouping: MCOR_EER_FRAC_TYPE = 32,
        do_float16: DO_F16_TYPE = True,
        do_dose_weighting: MCOR_DO_DOSE_WEIGHTING_TYPE = True,
        group_for_ps: MCOR_SUM_EVERY_E_TYPE = 4.0,
        # Motion correction
        bfactor: MCOR_BFACTOR_TYPE = 150,
        group_frames: MCOR_GROUP_FRAMES_TYPE = 1,
        bin_factor: MCOR_BIN_FACTOR_TYPE = 1,
        fn_defect: MCOR_DEFECT_FILE_TYPE = "",
        fn_gain_ref: MCOR_GAIN_REF_TYPE = "",
        gain_rot: MCOR_GAIN_ROT_TYPE = "No rotation (0)",
        gain_flip: MCOR_GAIN_FLIP_TYPE = "No flipping (0)",
        patch: MCOR_PATCH_TYPE = (1, 1),
        gpu_ids: GPU_IDS_TYPE = "0",
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class MotionCorrOwnJob(_MotionCorrJobBase):
    """Motion correction using RELION's implementation (CPU)."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.motioncorr.own"

    @classmethod
    def job_title(cls):
        return "Motion Correction (RELION Implementation)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_own_motioncor"] = True
        kwargs["other_motioncor2_args"] = ""
        kwargs["gpu_ids"] = ""
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("do_own_motioncor", None)
        kwargs.pop("other_motioncor2_args", None)
        kwargs.pop("gpu_ids", None)
        return kwargs

    def run(
        self,
        input_star_mics: IN_MOVIES = "",
        first_frame_sum: MCOR_FIRST_FRAME_SUM_TYPE = 1,
        last_frame_sum: MCOR_LAST_FRAME_SUM_TYPE = -1,
        dose_per_frame: MCOR_DOSE_PER_FRAME_TYPE = 1.0,
        pre_exposure: MCOR_PRE_EXPOSURE_TYPE = 0.0,
        eer_grouping: MCOR_EER_FRAC_TYPE = 32,
        do_float16: DO_F16_TYPE = True,
        do_dose_weighting: MCOR_DO_DOSE_WEIGHTING_TYPE = True,
        do_save_noDW: MCOR_DO_SAVE_NO_DW_TYPE = False,
        do_save_ps: MCOR_DO_SAVE_PS_TYPE = True,
        group_for_ps: MCOR_SUM_EVERY_E_TYPE = 4.0,
        # Motion correction
        bfactor: MCOR_BFACTOR_TYPE = 150,
        group_frames: MCOR_GROUP_FRAMES_TYPE = 1,
        bin_factor: MCOR_BIN_FACTOR_TYPE = 1,
        fn_defect: MCOR_DEFECT_FILE_TYPE = "",
        fn_gain_ref: MCOR_GAIN_REF_TYPE = "",
        gain_rot: MCOR_GAIN_ROT_TYPE = "No rotation (0)",
        gain_flip: MCOR_GAIN_FLIP_TYPE = "No flipping (0)",
        patch: MCOR_PATCH_TYPE = (1, 1),
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets: dict[str, ValueWidget]) -> None:
        @widgets["do_save_ps"].changed.connect
        def _on_do_float16_changed(value: bool):
            widgets["group_for_ps"].enabled = not value

        _on_do_float16_changed(widgets["do_save_ps"].value)  # initialize


class CtfEstimationJob(_Relion5Job):
    """Contrast transfer function (CTF) estimation using CTFFIND4."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.ctffind.ctffind4"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_ctffind_exe"] = _configs.get_ctffind4_exe()
        if "phase_range" in kwargs:
            kwargs["phase_min"], kwargs["phase_max"], kwargs["phase_step"] = kwargs.pop(
                "phase_range"
            )
        if "dfrange" in kwargs:
            kwargs["dfmin"], kwargs["dfmax"], kwargs["dfstep"] = kwargs.pop("dfrange")
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("fn_ctffind_exe", None)
        kwargs["phase_range"] = (
            kwargs.pop("phase_min", 0),
            kwargs.pop("phase_max", 180),
            kwargs.pop("phase_step", 10),
        )
        kwargs["dfrange"] = (
            kwargs.pop("dfmin", 5000),
            kwargs.pop("dfmax", 50000),
            kwargs.pop("dfstep", 500),
        )
        return super().normalize_kwargs_inv(**kwargs)

    def run(
        self,
        # I/O
        input_star_mics: IN_MICROGRAPHS = "",
        use_noDW: Annotated[
            bool, {"label": "Use micrographs without dose-weighting", "group": "I/O"}
        ] = False,
        do_phaseshift: Annotated[
            bool, {"label": "Estimate phase shifts", "group": "I/O"}
        ] = False,
        phase_range: Annotated[
            tuple[float, float, float],
            {"label": "Phase shift min/max/step (deg)", "group": "I/O"},
        ] = (0, 180, 10),
        dast: Annotated[
            float, {"label": "Amount of astigmatism (A)", "group": "I/O"}
        ] = 100,
        # CTFFIND
        use_given_ps: Annotated[
            bool, {"label": "Use power spectra from MotionCorr", "group": "CTFFIND"}
        ] = True,
        slow_search: Annotated[
            bool, {"label": "Use exhaustive search", "group": "CTFFIND"}
        ] = False,
        ctf_win: Annotated[
            int, {"label": "CTF estimation window size (pix)", "group": "CTFFIND"}
        ] = -1,
        box: Annotated[int, {"label": "FFT box size (pix)", "group": "CTFFIND"}] = 512,
        resmax: Annotated[
            float, {"label": "Resolution max (A)", "group": "CTFFIND"}
        ] = 5,
        resmin: Annotated[
            float, {"label": "Resolution min (A)", "group": "CTFFIND"}
        ] = 30,
        dfrange: Annotated[
            tuple[float, float, float],
            {"label": "Defocus search range min/max/step (A)", "group": "CTFFIND"},
        ] = (5000, 50000, 500),
        # Running
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets: dict[str, ValueWidget]) -> None:
        @widgets["do_phaseshift"].changed.connect
        def _on_do_phaseshift_changed(value: bool):
            widgets["phase_range"].enabled = value

        widgets["phase_range"].enabled = False


class ManualPickJob(_Relion5Job):
    """Manual particle picking."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.manualpick"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        filter_method = kwargs.pop("filter_method", "Band-pass")
        kwargs["do_topaz_denoise"] = filter_method == "Topaz"
        kwargs["do_fom_threshold"] = kwargs["minimum_pick_fom"] is not None
        if kwargs["do_fom_threshold"]:
            kwargs["minimum_pick_fom"] = 0
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs["filter_method"] = (
            "Topaz" if kwargs.pop("do_topaz_denoise", False) else "Band-pass"
        )
        if not kwargs.pop("do_fom_threshold", False):
            kwargs["minimum_pick_fom"] = None
        for name in ["do_queue", "min_dedicated"]:
            kwargs.pop(name, None)
        return kwargs

    def run(
        self,
        fn_in: IN_MICROGRAPHS = "",
        do_startend: Annotated[
            bool, {"label": "Pick star-end coordinates helices", "group": "I/O"}
        ] = False,
        minimum_pick_fom: Annotated[
            float | None,
            {"label": "Minimum autopick FOM", "min": -10, "max": 10, "group": "I/O"},
        ] = None,
        # Display
        diameter: Annotated[
            float, {"label": "Particle diameter (A)", "group": "Display"}
        ] = 100,
        micscale: Annotated[
            float, {"label": "Scale for micrographs", "group": "Display"}
        ] = 0.2,
        sigma_contrast: Annotated[
            float, {"label": "Sigma contrast", "group": "Display"}
        ] = 3,
        white_val: Annotated[float, {"label": "White value", "group": "Display"}] = 0,
        black_val: Annotated[float, {"label": "Black value", "group": "Display"}] = 0,
        angpix: Annotated[float, {"label": "Pixel size (A)", "group": "Display"}] = -1,
        filter_method: Annotated[
            str,
            {
                "label": "Denoising method",
                "choices": ["Band-pass", "Topaz"],
                "group": "Display",
            },
        ] = "Band-pass",
        lowpass: Annotated[
            float, {"label": "Lowpass filter (A)", "group": "Display"}
        ] = 20,
        highpass: Annotated[
            float, {"label": "Highpass filter (A)", "group": "Display"}
        ] = -1,
        # Colors
        do_color: Annotated[
            bool, {"label": "Color particles by metadata", "group": "Colors"}
        ] = False,
        color_label: Annotated[
            str, {"label": "Color by this label", "group": "Colors"}
        ] = "rlnAutopickFigureOfMerit",
        fn_color: Annotated[
            str, {"label": "STAR file with color label", "group": "Colors"}
        ] = "",
        blue_value: Annotated[float, {"label": "Blue value", "group": "Colors"}] = 0,
        red_value: Annotated[float, {"label": "Red value", "group": "Colors"}] = 2,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["filter_method"].changed.connect
        def _on_filter_method_changed(value: str):
            widgets["lowpass"].enabled = value == "Band-pass"
            widgets["highpass"].enabled = value == "Band-pass"

        _on_filter_method_changed(widgets["filter_method"].value)  # initialize


class _AutoPickJob(_Relion5Job):
    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["continue_manual"] = False
        # template pick
        for key, value in [
            ("do_refs", False),
            ("fn_refs_autopick", ""),
            ("do_ref3d", False),
            ("fn_ref3d_autopick", ""),
            ("ref3d_symmetry", "C1"),
            ("ref3d_sampling", "30 degrees"),
            ("lowpass", 20),
            ("highpass", -1),
            ("angpix_ref", -1),
            ("psi_sampling_autopick", 5),
            ("do_invert_refs", True),
            ("do_ctf_autopick", True),
            ("do_ignore_first_ctfpeak_autopick", False),
            # LoG
            ("do_log", False),
            ("log_diam_min", 200),
            ("log_diam_max", 250),
            ("log_invert", False),
            ("log_maxres", 20),
            ("log_adjust_thr", 0),
            ("log_upper_thr", 999),
            # Topaz
            ("do_topaz", False),
            ("do_topaz_filaments", False),
            ("do_topaz_pick", False),
            ("do_topaz_train", False),
            ("do_topaz_train_parts", False),
            ("fn_topaz_exe", "relion_python_topaz"),
            ("topaz_filament_threshold", -5),
            ("topaz_hough_length", -1),
            ("topaz_model", ""),
            ("topaz_nr_particles", -1),
            ("topaz_other_args", ""),
            ("topaz_particle_diameter", -1),
            ("topaz_train_parts", ""),
            ("topaz_train_picks", ""),
        ]:
            kwargs.setdefault(key, value)

        # others
        kwargs["use_gpu"] = kwargs["gpu_ids"] != ""
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("use_gpu", None)
        return kwargs


class AutoPickLogJob(_AutoPickJob):
    """Automatic particle picking using Laplacian of Gaussian filter."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.autopick.log"

    @classmethod
    def job_title(cls):
        return "LoG Pick"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_log"] = True
        kwargs["minavgnoise_autopick"] = -999
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("minavgnoise_autopick", None)
        keys_to_pop = [
            "continue_manual",
            "do_log",
            "do_ref3d",
            "do_refs",
            "log_upper_thr",
        ]
        for key in kwargs:
            if key.startswith(("do_topaz", "topaz_")):
                keys_to_pop.append(key)
        for key in keys_to_pop:
            kwargs.pop(key, None)
        return kwargs

    def run(
        self,
        fn_input_autopick: IN_MICROGRAPHS = "",
        angpix: Annotated[
            float, {"label": "Micrograph pixel size (A)", "group": "IO"}
        ] = -1,
        # Laplacian
        log_diam_min: Annotated[
            float, {"label": "Min diameter for LoG filter (A)", "group": "Laplacian"}
        ] = 200,
        log_diam_max: Annotated[
            float, {"label": "Max diameter for LoG filter (A)", "group": "Laplacian"}
        ] = 250,
        log_invert: Annotated[
            bool, {"label": "Dark background", "group": "Laplacian"}
        ] = False,
        log_maxres: Annotated[
            float, {"label": "Max resolution to consider (A)", "group": "Laplacian"}
        ] = 20,
        log_adjust_thr: Annotated[
            float, {"label": "Adjust default threshold (stddev)", "group": "Laplacian"}
        ] = 0,
        log_upper_thr: Annotated[
            float, {"label": "Upper threshold (stddev)", "group": "Laplacian"}
        ] = 999,
        # Autopicking
        threshold_autopick: Annotated[
            float, {"label": "Picking threshold", "group": "Autopicking"}
        ] = 0.05,
        mindist_autopick: Annotated[
            float, {"label": "Min inter-particle distance (A)", "group": "Autopicking"}
        ] = 100,
        maxstddevnoise_autopick: Annotated[
            float, {"label": "Max stddev noise", "group": "Autopicking"}
        ] = 1.1,
        do_write_fom_maps: Annotated[
            bool, {"label": "Write FOM maps", "group": "Autopicking"}
        ] = False,
        do_read_fom_maps: Annotated[
            bool, {"label": "Read FOM maps", "group": "Autopicking"}
        ] = False,
        shrink: Annotated[
            float, {"label": "Shrink factor", "group": "Autopicking"}
        ] = 0,
        gpu_ids: GPU_IDS_TYPE = "",
        # Helical
        do_pick_helical_segments: Annotated[
            bool, {"label": "Pick 2D helical segments", "group": "Helix"}
        ] = False,
        helical_tube_outer_diameter: HELICAL_TUBE_DIAMETER_TYPE = 200,
        helical_tube_length_min: Annotated[
            float, {"label": "Minimum length (A)", "group": "Helix"}
        ] = -1,
        helical_tube_kappa_max: Annotated[
            float, {"label": "Maximum curvature (kappa)", "group": "Helix"}
        ] = 0.1,
        helical_nr_asu: HELICAL_NR_ASU_TYPE = 1,
        helical_rise: HELICAL_RISE_TYPE = -1,
        do_amyloid: Annotated[
            bool, {"label": "Pick amyloid segments", "group": "Helix"}
        ] = False,
        # Running
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class AutoPickTemplate2DJob(_AutoPickJob):
    """Automatic particle picking using template matching."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.autopick.ref2d"

    @classmethod
    def job_title(cls):
        return "Template Pick"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_refs"] = True
        kwargs["do_ref3d"] = False
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        keys_to_pop = [
            "continue_manual",
            "do_log",
            "do_ref3d",
            "do_refs",
            "log_upper_thr",
        ]
        for key in kwargs:
            if key.startswith(("do_topaz", "topaz_")):
                keys_to_pop.append(key)
        for key in keys_to_pop:
            kwargs.pop(key, None)
        return kwargs

    def run(
        self,
        fn_input_autopick: IN_MICROGRAPHS = "",
        angpix: Annotated[
            float, {"label": "Micrograph pixel size (A)", "group": "I/O"}
        ] = -1,
        # References
        fn_refs_autopick: Annotated[
            str, {"label": "2D reference", "group": "References"}
        ] = "",
        lowpass: Annotated[
            float, {"label": "Lowpass filter references", "group": "References"}
        ] = 20,
        highpass: Annotated[
            float, {"label": "Highpass filter micrographs", "group": "References"}
        ] = -1,
        angpix_ref: Annotated[
            float, {"label": "Reference pixel size", "group": "References"}
        ] = -1,
        psi_sampling_autopick: Annotated[
            float, {"label": "In-plane angular sampling (deg)", "group": "References"}
        ] = 5,
        do_invert_refs: Annotated[
            float, {"label": "References have inverted contrast", "group": "References"}
        ] = True,
        do_ctf_autopick: Annotated[
            float, {"label": "References are CTF corrected", "group": "References"}
        ] = True,
        do_ignore_first_ctfpeak_autopick: Annotated[
            float, {"label": "Ignore CTFs until first peak", "group": "References"}
        ] = False,
        # Autopicking
        threshold_autopick: Annotated[
            float, {"label": "Picking threshold", "group": "Autopicking"}
        ] = 0.05,
        mindist_autopick: Annotated[
            float, {"label": "Min inter-particle distance (A)", "group": "Autopicking"}
        ] = 100,
        maxstddevnoise_autopick: Annotated[
            float, {"label": "Max stddev noise", "group": "Autopicking"}
        ] = 1.1,
        minavgnoise_autopick: Annotated[
            float, {"label": "Min avg noise", "group": "Autopicking"}
        ] = -999,
        do_write_fom_maps: Annotated[
            bool, {"label": "Write FOM maps", "group": "Autopicking"}
        ] = False,
        do_read_fom_maps: Annotated[
            bool, {"label": "Read FOM maps", "group": "Autopicking"}
        ] = False,
        shrink: Annotated[
            float, {"label": "Shrink factor", "group": "Autopicking"}
        ] = 0,
        gpu_ids: GPU_IDS_TYPE = "",
        # Helical
        do_pick_helical_segments: Annotated[
            bool, {"label": "Pick 2D helical segments", "group": "Helix"}
        ] = False,
        helical_tube_outer_diameter: HELICAL_TUBE_DIAMETER_TYPE = 200,
        helical_tube_length_min: Annotated[
            float, {"label": "Minimum length (A)", "group": "Helix"}
        ] = -1,
        helical_tube_kappa_max: Annotated[
            float, {"label": "Maximum curvature (kappa)", "group": "Helix"}
        ] = 0.1,
        helical_nr_asu: HELICAL_NR_ASU_TYPE = 1,
        helical_rise: HELICAL_RISE_TYPE = -1,
        do_amyloid: Annotated[
            bool, {"label": "Pick amyloid segments", "group": "Helix"}
        ] = False,
        # Running
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


REF3D_SAMPLING = Literal[
    "30 degrees",
    "15 degrees",
    "7.5 degrees",
    "3.7 degrees",
    "1.8 degrees",
    "0.9 degrees",
    "0.5 degrees",
    "0.2 degrees",
    "0.1 degrees",
]


class AutoPickTemplate3DJob(_AutoPickJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.autopick.ref3d"

    @classmethod
    def job_title(cls):
        return "Template Pick 3D"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_refs"] = kwargs["do_ref3d"] = True
        kwargs["fn_refs_autopick"] = ""
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        return kwargs

    def run(
        self,
        fn_input_autopick: IN_MICROGRAPHS = "",
        fn_ref3d_autopick: REF_TYPE = "",
        angpix: Annotated[
            float, {"label": "Micrograph pixel size (A)", "group": "I/O"}
        ] = -1,
        # References
        ref3d_symmetry: Annotated[
            str, {"label": "Symmetry", "group": "References"}
        ] = "C1",
        ref3d_sampling: Annotated[
            REF3D_SAMPLING, {"label": "3D angular sampling", "group": "References"}
        ] = "30 degrees",
        lowpass: Annotated[
            float, {"label": "Lowpass filter references (A)", "group": "References"}
        ] = 20,
        highpass: Annotated[
            float, {"label": "Highpass filter micrographs (A)", "group": "References"}
        ] = -1,
        angpix_ref: Annotated[
            float, {"label": "Reference pixel size (A)", "group": "References"}
        ] = -1,
        psi_sampling_autopick: Annotated[
            float, {"label": "In-plane angular sampling (deg)", "group": "References"}
        ] = 5,
        do_invert_refs: Annotated[
            bool, {"label": "References have inverted contrast", "group": "References"}
        ] = True,
        do_ctf_autopick: Annotated[
            bool, {"label": "References are CTF corrected", "group": "References"}
        ] = True,
        do_ignore_first_ctfpeak_autopick: Annotated[
            bool, {"label": "Ignore CTFs until first peak", "group": "References"}
        ] = False,
        # Autopicking
        threshold_autopick: Annotated[
            float, {"label": "Picking threshold", "group": "Autopicking"}
        ] = 0.05,
        mindist_autopick: Annotated[
            float, {"label": "Min inter-particle distance (A)", "group": "Autopicking"}
        ] = 100,
        maxstddevnoise_autopick: Annotated[
            float, {"label": "Max stddev noise", "group": "Autopicking"}
        ] = 1.1,
        minavgnoise_autopick: Annotated[
            float, {"label": "Min avg noise", "group": "Autopicking"}
        ] = -999,
        do_write_fom_maps: Annotated[
            bool, {"label": "Write FOM maps", "group": "Autopicking"}
        ] = False,
        do_read_fom_maps: Annotated[
            bool, {"label": "Read FOM maps", "group": "Autopicking"}
        ] = False,
        shrink: Annotated[
            float, {"label": "Shrink factor", "group": "Autopicking"}
        ] = 0,
        gpu_ids: GPU_IDS_TYPE = "",
        # Helical
        do_pick_helical_segments: Annotated[
            bool, {"label": "Pick 2D helical segments", "group": "Helix"}
        ] = False,
        helical_tube_outer_diameter: HELICAL_TUBE_DIAMETER_TYPE = 200,
        helical_tube_length_min: Annotated[
            float, {"label": "Minimum length (A)", "group": "Helix"}
        ] = -1,
        helical_tube_kappa_max: Annotated[
            float, {"label": "Maximum curvature (kappa)", "group": "Helix"}
        ] = 0.1,
        helical_nr_asu: HELICAL_NR_ASU_TYPE = 1,
        helical_rise: HELICAL_RISE_TYPE = -1,
        do_amyloid: Annotated[
            bool, {"label": "Pick amyloid segments", "group": "Helix"}
        ] = False,
        # Running
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_pick_helical_segments"].changed.connect
        def _on_do_pick_helical_segments_changed(value: bool):
            widgets["helical_tube_outer_diameter"].enabled = value
            widgets["helical_tube_length_min"].enabled = value
            widgets["helical_tube_kappa_max"].enabled = value
            widgets["helical_nr_asu"].enabled = value
            widgets["helical_rise"].enabled = value
            widgets["do_amyloid"].enabled = value

        _on_do_pick_helical_segments_changed(
            widgets["do_pick_helical_segments"].value
        )  # initialize


class AutoPickTopazTrain(_AutoPickJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.autopick.topaz.train"

    @classmethod
    def job_title(cls):
        return "Topaz Train"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_topaz"] = True
        kwargs["do_topaz_train"] = True
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        return kwargs

    def run(
        self,
        fn_input_autopick: IN_MICROGRAPHS = "",
        angpix: Annotated[
            float, {"label": "Micrograph pixel size (A)", "group": "IO"}
        ] = -1,
        # Topaz
        fn_topaz_exe: Annotated[
            str, {"label": "Topaz executable", "group": "Topaz"}
        ] = "relion_python_topaz",
        topaz_particle_diameter: Annotated[
            float, {"label": "Particle diameter (A)", "group": "Topaz"}
        ] = -1,
        topaz_nr_particles: Annotated[
            float, {"label": "Number of particles per micrographs", "group": "Topaz"}
        ] = -1,
        do_topaz_train_parts: Annotated[
            bool, {"label": "Train on a set of particles", "group": "Topaz"}
        ] = False,
        topaz_train_picks: Annotated[
            str, {"label": "Input picked coordinates for training", "group": "Topaz"}
        ] = "",
        topaz_train_parts: Annotated[
            str, {"label": "Particles STAR file for training", "group": "Topaz"}
        ] = "",
        # Autopicking
        threshold_autopick: Annotated[
            float, {"label": "Picking threshold", "group": "Autopicking"}
        ] = 0.05,
        mindist_autopick: Annotated[
            float, {"label": "Min inter-particle distance (A)", "group": "Autopicking"}
        ] = 100,
        maxstddevnoise_autopick: Annotated[
            float, {"label": "Max stddev noise", "group": "Autopicking"}
        ] = 1.1,
        do_write_fom_maps: Annotated[
            bool, {"label": "Write FOM maps", "group": "Autopicking"}
        ] = False,
        do_read_fom_maps: Annotated[
            bool, {"label": "Read FOM maps", "group": "Autopicking"}
        ] = False,
        shrink: Annotated[
            float, {"label": "Shrink factor", "group": "Autopicking"}
        ] = 0,
        gpu_ids: GPU_IDS_TYPE = "",
        # Helical
        do_pick_helical_segments: Annotated[
            bool, {"label": "Pick 2D helical segments", "group": "Helix"}
        ] = False,
        helical_tube_outer_diameter: HELICAL_TUBE_DIAMETER_TYPE = 200,
        helical_tube_length_min: Annotated[
            float, {"label": "Minimum length (A)", "group": "Helix"}
        ] = -1,
        helical_tube_kappa_max: Annotated[
            float, {"label": "Maximum curvature (kappa)", "group": "Helix"}
        ] = 0.1,
        helical_nr_asu: HELICAL_NR_ASU_TYPE = 1,
        helical_rise: HELICAL_RISE_TYPE = -1,
        do_amyloid: Annotated[
            bool, {"label": "Pick amyloid segments", "group": "Helix"}
        ] = False,
        # Running
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets: dict[str, ValueWidget]) -> None:
        @widgets["do_topaz_train_parts"].changed.connect
        def _on_do_topaz_train_parts_changed(value: bool):
            widgets["topaz_train_parts"].enabled = value
            widgets["topaz_train_picks"].enabled = not value

        _on_do_topaz_train_parts_changed(
            widgets["do_topaz_train_parts"].value
        )  # initialize


class AutoPickTopazPick(_AutoPickJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.autopick.topaz.pick"

    @classmethod
    def job_title(cls):
        return "Topaz Pick"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_topaz"] = True
        kwargs["do_topaz_pick"] = True
        return kwargs

    def run(
        self,
        fn_input_autopick: IN_MICROGRAPHS = "",
        angpix: Annotated[
            float, {"label": "Micrograph pixel size (A)", "group": "IO"}
        ] = -1,
        # Topaz
        fn_topaz_exe: Annotated[
            str, {"label": "Topaz executable", "group": "Topaz"}
        ] = "relion_python_topaz",
        topaz_particle_diameter: Annotated[
            float, {"label": "Particle diameter (A)", "group": "Topaz"}
        ] = -1,
        topaz_model: Annotated[
            str, {"label": "Trained Topaz model", "group": "Topaz"}
        ] = "",
        do_topaz_filaments: Annotated[
            bool, {"label": "Pick filaments", "group": "Topaz"}
        ] = False,
        topaz_filament_threshold: Annotated[
            float, {"label": "Filament threshold", "group": "Topaz"}
        ] = -5,
        topaz_hough_length: Annotated[
            float, {"label": "Hough length", "group": "Topaz"}
        ] = -1,
        topaz_other_args: Annotated[
            str, {"label": "Additional Topaz arguments", "group": "Topaz"}
        ] = "",
        # Autopicking
        threshold_autopick: Annotated[
            float, {"label": "Picking threshold", "group": "Autopicking"}
        ] = 0.05,
        mindist_autopick: Annotated[
            float, {"label": "Min inter-particle distance (A)", "group": "Autopicking"}
        ] = 100,
        maxstddevnoise_autopick: Annotated[
            float, {"label": "Max stddev noise", "group": "Autopicking"}
        ] = 1.1,
        do_write_fom_maps: Annotated[
            bool, {"label": "Write FOM maps", "group": "Autopicking"}
        ] = False,
        do_read_fom_maps: Annotated[
            bool, {"label": "Read FOM maps", "group": "Autopicking"}
        ] = False,
        shrink: Annotated[
            float, {"label": "Shrink factor", "group": "Autopicking"}
        ] = 0,
        gpu_ids: GPU_IDS_TYPE = "",
        # Helical
        do_pick_helical_segments: Annotated[
            bool, {"label": "Pick 2D helical segments", "group": "Helix"}
        ] = False,
        helical_tube_outer_diameter: HELICAL_TUBE_DIAMETER_TYPE = 200,
        helical_tube_length_min: Annotated[
            float, {"label": "Minimum length (A)", "group": "Helix"}
        ] = -1,
        helical_tube_kappa_max: Annotated[
            float, {"label": "Maximum curvature (kappa)", "group": "Helix"}
        ] = 0.1,
        helical_nr_asu: HELICAL_NR_ASU_TYPE = 1,
        helical_rise: HELICAL_RISE_TYPE = -1,
        do_amyloid: Annotated[
            bool, {"label": "Pick amyloid segments", "group": "Helix"}
        ] = False,
        # Running
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ExtractJobBase(_Relion5Job):
    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)

        # common defaults
        for key, value in [
            ("star_mics", ""),
            ("coords_suffix", ""),
            ("do_reextract", False),
            ("fndata_reextract", ""),
            ("do_reset_offsets", False),
            ("do_recenter", True),
        ]:
            kwargs.setdefault(key, value)

        kwargs["recenter_x"], kwargs["recenter_y"], kwargs["recenter_z"] = (0, 0, 0)

        # normalize
        kwargs["do_rescale"] = kwargs["extract_size"] != kwargs.get["rescale"]
        kwargs["do_fom_threshold"] = kwargs.get("minimum_pick_fom", None) is not None
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("do_reextract", None)
        kwargs.pop("do_recenter", None)
        if kwargs.pop("do_fom_threshold"):
            pass
        else:
            kwargs["minimum_pick_fom"] = None
        return kwargs


class ExtractJob(ExtractJobBase):
    """Particle extraction from micrographs."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.extract"

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        for name in [
            "fndata_reextract",
            "do_reset_offsets",
            "do_recenter",
            "recenter_x",
            "recenter_y",
            "recenter_z",
            "do_rescale",
        ]:
            kwargs.pop(name, None)
        return kwargs

    def run(
        self,
        # I/O
        star_mics: IN_MICROGRAPHS = "",
        coords_suffix: IN_COORDINATES = "",
        do_float16: DO_F16_TYPE = True,
        # Extract
        extract_size: EXTRACT_SIZE_TYPE = 128,
        rescale: EXTRACT_RESCALE_TYPE = 128,
        do_invert: EXTRACT_INVERT_TYPE = True,
        do_norm: EXTRACT_NORM_TYPE = True,
        bg_diameter: EXTRACT_DIAMETER_TYPE = -1,
        white_dust: EXTRACT_WIGHT_DUST_TYPE = -1,
        black_dust: EXTRACT_BLACK_DUST_TYPE = -1,
        minimum_pick_fom: Annotated[
            float | None, {"label": "Minimum autopick FOM", "group": "Extract"}
        ] = None,
        # Helix
        do_extract_helix: DO_HELIX_TYPE = False,
        helical_tube_outer_diameter: HELICAL_TUBE_DIAMETER_TYPE = 200,
        helical_bimodal_angular_priors: Annotated[
            bool, {"label": "Use bimodal angular priors", "group": "Helix"}
        ] = True,
        do_extract_helical_tubes: Annotated[
            bool, {"label": "Coordinates are star-end only", "group": "Helix"}
        ] = True,
        do_cut_into_segments: Annotated[
            bool, {"label": "Cut helical tubes into segments"}
        ] = True,
        helical_nr_asu: HELICAL_NR_ASU_TYPE = 1,
        helical_rise: HELICAL_RISE_TYPE = 1,
        # Running
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ReExtractJob(ExtractJobBase):
    """Particle re-extraction from micrographs."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.extract.reextract"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_reextract"] = True

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        for name in ["star_mics", "coords_suffix", "do_rescale"]:
            kwargs.pop(name, None)
        kwargs["recenter"] = tuple(kwargs.pop(f"recenter_{x}", 0) for x in "xyz")
        return kwargs

    def run(
        self,
        # I/O
        fndata_reextract: Annotated[
            str, {"label": "STAR file with refined particles", "group": "I/O"}
        ] = "",
        do_reset_offsets: Annotated[
            bool, {"label": "Reset refined offsets to zero", "group": "I/O"}
        ] = False,
        do_recenter: Annotated[
            bool, {"label": "Recenter refined coordinates", "group": "I/O"}
        ] = True,
        recenter: Annotated[tuple[float], {"group": "I/O"}] = (0, 0, 0),
        do_float16: DO_F16_TYPE = True,
        # Extract
        extract_size: EXTRACT_SIZE_TYPE = 128,
        rescale: EXTRACT_RESCALE_TYPE = 128,
        do_invert: EXTRACT_INVERT_TYPE = True,
        do_norm: EXTRACT_NORM_TYPE = True,
        bg_diameter: EXTRACT_DIAMETER_TYPE = -1,
        white_dust: EXTRACT_WIGHT_DUST_TYPE = -1,
        black_dust: EXTRACT_BLACK_DUST_TYPE = -1,
        minimum_pick_fom: Annotated[
            float | None, {"label": "Minimum autopick FOM", "group": "Extract"}
        ] = None,
        # Helix
        do_extract_helix: DO_HELIX_TYPE = False,
        helical_tube_outer_diameter: HELICAL_TUBE_DIAMETER_TYPE = 200,
        helical_bimodal_angular_priors: Annotated[
            bool, {"label": "Use bimodal angular priors", "group": "Helix"}
        ] = True,
        do_extract_helical_tubes: Annotated[
            bool, {"label": "Coordinates are star-end only", "group": "Helix"}
        ] = True,
        do_cut_into_segments: Annotated[
            bool, {"label": "Cut helical tubes into segments"}
        ] = True,
        helical_nr_asu: HELICAL_NR_ASU_TYPE = 1,
        helical_rise: HELICAL_RISE_TYPE = 1,
        # Running
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class Class2DJob(_Relion5Job):
    @classmethod
    def type_label(cls) -> str:
        return "relion.class2d"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["fn_cont"] = ""
        # default
        for key, value in [
            ("do_em", False),
            ("nr_iter_em", 25),
            ("do_grad", True),
            ("nr_iter_grad", 200),
        ]:
            kwargs.setdefault(key, value)

        algo = kwargs.pop("algorithm")
        if algo["algorith"] == "EM":
            kwargs["do_em"] = True
            kwargs["nr_iter_em"] = algo["niter"]
        else:
            kwargs["do_grad"] = True
            kwargs["nr_iter_grad"] = algo["niter"]
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        nr_iter_em = kwargs.pop("nr_iter_em", 25)
        nr_iter_grad = kwargs.pop("nr_iter_grad", 200)
        if kwargs.pop("do_em", False):
            kwargs["algorithm"] = {
                "algorithm": "EM",
                "niter": nr_iter_em,
            }
        else:
            kwargs["algorithm"] = {
                "algorithm": "VDAM",
                "niter": nr_iter_grad,
            }
        # remove internal
        kwargs.pop("do_grad", None)
        kwargs.pop("fn_cont", None)
        return kwargs

    def run(
        self,
        # I/O
        fn_img: IMG_TYPE = "",
        # CTF
        do_ctf_correction: DO_CTF_TYPE = True,
        ctf_intact_first_peak: IGNORE_CTF_TYPE = False,
        # Optimisation
        nr_classes: Annotated[
            int, {"label": "Number of classes", "group": "Optimisation"}
        ] = 50,
        tau_fudge: T_TYPE = 2,
        algorithm: Annotated[
            dict,
            {
                "label": "Algorithm",
                "widget_type": Class2DAlgorithmEdit,
                "group": "Optimisation",
            },
        ] = {"algorithm": "VDAM", "niter": 200},
        particle_diameter: MASK_DIAMETER_TYPE = 200,
        do_zero_mask: MASK_WITH_ZEROS_TYPE = True,
        highres_limit: Annotated[
            float, {"label": "Limit resolution to (A)", "group": "Optimisation"}
        ] = -1,
        do_center: Annotated[
            bool, {"label": "Center class averages", "group": "Optimisation"}
        ] = True,
        # Sampling
        dont_skip_align: DONT_SKIP_ALIGN_TYPE = True,
        psi_sampling: Annotated[
            float, {"label": "In-plane angular sampling (deg)", "group": "Sampling"}
        ] = 6,
        offset_range: Annotated[float, {"label": "Offset search range (pix)"}] = 5,
        offset_step: Annotated[float, {"label": "Offset search step (pix)"}] = 1,
        allow_coarser: ALLOW_COARSER_SAMPLING_TYPE = False,
        # Helix
        do_helix: Annotated[
            bool, {"label": "Classify 2D helical segments", "group": "Helix"}
        ] = False,
        helical_tube_outer_diameter: HELICAL_TUBE_DIAMETER_TYPE = 200,
        do_bimodal_psi: Annotated[
            bool, {"label": "Do bimodal angular searches", "group": "Helix"}
        ] = True,
        range_psi: Annotated[
            float, {"label": "Angular search range (deg)", "group": "Helix"}
        ] = 6.0,
        do_restrict_xoff: Annotated[
            bool, {"label": "Restrict helical offsets to rise", "group": "Helix"}
        ] = True,
        helical_rise: HELICAL_RISE_TYPE = 4.75,
        # Compute
        do_parallel_discio: USE_PARALLEL_DISC_IO_TYPE = True,
        nr_pool: NUM_POOL_TYPE = 3,
        do_preread_images: DO_PREREAD_TYPE = False,
        use_scratch: USE_SCRATCH_TYPE = False,
        do_combine_thru_disc: DO_COMBINE_THRU_DISC_TYPE = False,
        gpu_ids: GPU_IDS_TYPE = "",
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_helix"].changed.connect
        def _on_do_helix_changed(value: bool):
            widgets["helical_tube_outer_diameter"].enabled = value
            widgets["do_bimodal_psi"].enabled = value
            widgets["range_psi"].enabled = value
            widgets["do_restrict_xoff"].enabled = value
            widgets["helical_rise"].enabled = value

        _on_do_helix_changed(widgets["do_helix"].value)  # initialize


class InitialModelJob(_Relion5Job):
    @classmethod
    def type_label(cls) -> str:
        return "relion.initialmodel"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_cont"] = ""
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("fn_cont", None)
        return super().normalize_kwargs_inv(**kwargs)

    def run(
        self,
        fn_img: IN_PARTICLES = None,
        # CTF
        do_ctf_correction: DO_CTF_TYPE = True,
        ctf_intact_first_peak: IGNORE_CTF_TYPE = False,
        # Optimisation
        nr_iter: NUM_ITER_TYPE = 200,
        tau_fudge: T_TYPE = 4,
        nr_classes: NUM_CLASS_TYPE = 1,
        particle_diameter: MASK_DIAMETER_TYPE = 200,
        do_solvent: Annotated[
            bool,
            {
                "label": "Flatten and enforce non-negative solvent",
                "group": "Optimisation",
            },
        ] = True,
        sym_name: Annotated[str, {"label": "Symmetry", "group": "Optimisation"}] = "C1",
        do_run_C1: Annotated[
            bool,
            {"label": "Run in C1 and apply symmetry later", "group": "Optimisation"},
        ] = True,
        # Compute
        do_parallel_discio: USE_PARALLEL_DISC_IO_TYPE = True,
        nr_pool: NUM_POOL_TYPE = 3,
        do_preread_images: DO_PREREAD_TYPE = False,
        use_scratch: USE_SCRATCH_TYPE = False,
        do_combine_thru_disc: DO_COMBINE_THRU_DISC_TYPE = False,
        gpu_ids: GPU_IDS_TYPE = "",
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_ctf_correction"].changed.connect
        def _on_do_ctf_correction_changed(value: bool):
            widgets["ctf_intact_first_peak"].enabled = value

        widgets["ctf_intact_first_peak"].enabled = widgets["do_ctf_correction"].value


class Class3DJobBase(_Relion5Job):
    """3D classification."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.class3d"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        if "helical_twist_range" in kwargs:
            (
                kwargs["helical_twist_min"],
                kwargs["helical_twist_max"],
                kwargs["helical_twist_inistep"],
            ) = kwargs.pop("helical_twist_range")
        if "helical_rise_range" in kwargs:
            (
                kwargs["helical_rise_min"],
                kwargs["helical_rise_max"],
                kwargs["helical_rise_inistep"],
            ) = kwargs.pop("helical_rise_range")
        if "rot_tilt_psi_range" in kwargs:
            kwargs["range_rot"], kwargs["range_tilt"], kwargs["range_psi"] = kwargs.pop(
                "rot_tilt_psi_range"
            )
        if "helical_tube_diameter_range" in kwargs:
            (
                kwargs["helical_tube_inner_diameter"],
                kwargs["helical_tube_outer_diameter"],
            ) = kwargs.pop("helical_tube_diameter_range")
        if "offset_range_step" in kwargs:
            kwargs["offset_range"], kwargs["offset_step"] = kwargs.pop(
                "offset_range_step"
            )
        kwargs["fn_cont"] = ""
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs["helical_twist_range"] = (
            kwargs.pop("helical_twist_min", 0),
            kwargs.pop("helical_twist_max", 0),
            kwargs.pop("helical_twist_inistep", 0),
        )
        kwargs["helical_rise_range"] = (
            kwargs.pop("helical_rise_min", 0),
            kwargs.pop("helical_rise_max", 0),
            kwargs.pop("helical_rise_inistep", 0),
        )
        kwargs["rot_tilt_psi_range"] = (
            kwargs.pop("range_rot", -1),
            kwargs.pop("range_tilt", 15),
            kwargs.pop("range_psi", 10),
        )
        kwargs["helical_tube_diameter_range"] = (
            kwargs.pop("helical_tube_inner_diameter", -1),
            kwargs.pop("helical_tube_outer_diameter", -1),
        )
        kwargs["offset_range_step"] = (
            kwargs.pop("offset_range", 5),
            kwargs.pop("offset_step", 1),
        )
        kwargs.pop("fn_cont", None)
        return super().normalize_kwargs_inv(**kwargs)

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_local_ang_searches"].changed.connect
        def _on_do_local_ang_searches_changed(value: bool):
            widgets["sigma_angles"].enabled = value
            widgets["relax_sym"].enabled = value

        @widgets["do_ctf_correction"].changed.connect
        def _on_do_ctf_correction_changed(value: bool):
            widgets["ctf_intact_first_peak"].enabled = value

        widgets["sigma_angles"].enabled = widgets["do_local_ang_searches"].value
        widgets["relax_sym"].enabled = widgets["do_local_ang_searches"].value
        widgets["ctf_intact_first_peak"].enabled = widgets["do_ctf_correction"].value

        _setup_helix_params(widgets)


class Class3DNoAlignmentJob(Class3DJobBase):
    @classmethod
    def command_id(cls):
        return super().command_id() + ".noalignment"

    @classmethod
    def param_matches(cls, job_params: dict[str, str]) -> bool:
        return job_params.get("dont_skip_align", "Yes") == "No"

    @classmethod
    def job_title(cls):
        return "3D Class (No Alignment)"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        # force no alignment
        kwargs["dont_skip_align"] = False
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("dont_skip_align", None)
        return kwargs

    def run(
        self,
        fn_img: IN_PARTICLES = "",
        fn_ref: REF_TYPE = "",
        fn_mask: MASK_TYPE = "",
        # Reference
        ref_correct_greyscale: REF_CORRECT_GRAY_TYPE = False,
        trust_ref_size: TRUST_REF_SIZE_TYPE = True,
        ini_high: INITIAL_LOWPASS_TYPE = 60,
        sym_name: REF_SYMMETRY_TYPE = "C1",
        # CTF
        do_ctf_correction: DO_CTF_TYPE = True,
        ctf_intact_first_peak: IGNORE_CTF_TYPE = False,
        # Optimisation
        nr_classes: NUM_CLASS_TYPE = 1,
        nr_iter: NUM_ITER_TYPE = 25,
        tau_fudge: T_TYPE = 1,
        particle_diameter: MASK_DIAMETER_TYPE = 200,
        do_zero_mask: MASK_WITH_ZEROS_TYPE = True,
        highres_limit: HIGH_RES_LIMIT_TYPE = -1,
        do_blush: DO_BLUSH_TYPE = False,
        # Helix
        do_helix: DO_HELIX_TYPE = False,
        helical_tube_diameter_range: HELICAL_TUBE_DIAMETER_RANGE_TYPE = (-1, -1),
        rot_tilt_psi_range: ROT_TILT_PSI_RANGE_TYPE = (-1, 15, 10),
        helical_range_distance: HELICAL_RANGE_DIST_TYPE = -1,
        keep_tilt_prior_fixed: KEEP_TILT_PRIOR_FIXED_TYPE = True,
        do_apply_helical_symmetry: DO_APPLY_HELICAL_SYMMETRY_TYPE = True,
        helical_twist_initial: HELICAL_TWIST_INITIAL_TYPE = 0,
        helical_rise_initial: HELICAL_RISE_INITIAL_TYPE = 0,
        helical_nr_asu: HELICAL_NR_ASU_TYPE = 1,
        helical_z_percentage: HELICAL_Z_PERCENTAGE_TYPE = 30,
        do_local_search_helical_symmetry: DO_LOCAL_SEARCH_HELICAL_SYMMETRY_TYPE = False,
        helical_twist_range: HELICAL_TWIST_RANGE_TYPE = (0, 0, 0),
        helical_rise_range: HELICAL_RISE_RANGE_TYPE = (0, 0, 0),
        # Compute
        do_fast_subsets: USE_FAST_SUBSET_TYPE = False,
        do_parallel_discio: USE_PARALLEL_DISC_IO_TYPE = True,
        use_scratch: USE_SCRATCH_TYPE = False,
        nr_pool: NUM_POOL_TYPE = 3,
        do_pad1: Annotated[bool, {"label": "Skip padding", "group": "Compute"}] = False,
        do_preread_images: DO_PREREAD_TYPE = False,
        do_combine_thru_disc: DO_COMBINE_THRU_DISC_TYPE = False,
        gpu_ids: GPU_IDS_TYPE = "",
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class Class3DJob(Class3DJobBase):
    @classmethod
    def command_id(cls):
        return super().command_id() + ".alignment"

    @classmethod
    def param_matches(cls, job_params: dict[str, str]) -> bool:
        return job_params.get("dont_skip_align", "Yes") == "Yes"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        # force no alignment
        kwargs["dont_skip_align"] = True
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("dont_skip_align", None)
        return kwargs

    def run(
        self,
        fn_img: IN_PARTICLES = "",
        fn_ref: REF_TYPE = "",
        fn_mask: MASK_TYPE = "",
        # Reference
        ref_correct_greyscale: REF_CORRECT_GRAY_TYPE = False,
        trust_ref_size: TRUST_REF_SIZE_TYPE = True,
        ini_high: INITIAL_LOWPASS_TYPE = 60,
        sym_name: REF_SYMMETRY_TYPE = "C1",
        # CTF
        do_ctf_correction: DO_CTF_TYPE = True,
        ctf_intact_first_peak: IGNORE_CTF_TYPE = False,
        # Optimisation
        nr_classes: NUM_CLASS_TYPE = 1,
        nr_iter: NUM_ITER_TYPE = 25,
        tau_fudge: T_TYPE = 1,
        particle_diameter: MASK_DIAMETER_TYPE = 200,
        do_zero_mask: MASK_WITH_ZEROS_TYPE = True,
        highres_limit: HIGH_RES_LIMIT_TYPE = -1,
        do_blush: DO_BLUSH_TYPE = False,
        # Sampling
        sampling: ANG_SAMPLING_TYPE = "7.5 degrees",
        offset_range_step: OFFSET_RANGE_STEP_TYPE = (5, 1),
        do_local_ang_searches: LOCAL_ANG_SEARCH_TYPE = False,
        sigma_angles: Annotated[
            float, {"label": "Local angular search range", "group": "Sampling"}
        ] = 5,
        relax_sym: RELAX_SYMMETRY_TYPE = "",
        allow_coarser: ALLOW_COARSER_SAMPLING_TYPE = False,
        # Helix
        do_helix: DO_HELIX_TYPE = False,
        helical_tube_diameter_range: HELICAL_TUBE_DIAMETER_RANGE_TYPE = (-1, -1),
        rot_tilt_psi_range: ROT_TILT_PSI_RANGE_TYPE = (-1, 15, 10),
        helical_range_distance: HELICAL_RANGE_DIST_TYPE = -1,
        keep_tilt_prior_fixed: KEEP_TILT_PRIOR_FIXED_TYPE = True,
        do_apply_helical_symmetry: DO_APPLY_HELICAL_SYMMETRY_TYPE = True,
        helical_twist_initial: HELICAL_TWIST_INITIAL_TYPE = 0,
        helical_rise_initial: HELICAL_RISE_INITIAL_TYPE = 0,
        helical_nr_asu: HELICAL_NR_ASU_TYPE = 1,
        helical_z_percentage: HELICAL_Z_PERCENTAGE_TYPE = 30,
        do_local_search_helical_symmetry: DO_LOCAL_SEARCH_HELICAL_SYMMETRY_TYPE = False,
        helical_twist_range: HELICAL_TWIST_RANGE_TYPE = (0, 0, 0),
        helical_rise_range: HELICAL_RISE_RANGE_TYPE = (0, 0, 0),
        # Compute
        do_fast_subsets: USE_FAST_SUBSET_TYPE = False,
        do_parallel_discio: USE_PARALLEL_DISC_IO_TYPE = True,
        use_scratch: USE_SCRATCH_TYPE = False,
        nr_pool: NUM_POOL_TYPE = 3,
        do_pad1: Annotated[bool, {"label": "Skip padding", "group": "Compute"}] = False,
        do_preread_images: DO_PREREAD_TYPE = False,
        do_combine_thru_disc: DO_COMBINE_THRU_DISC_TYPE = False,
        gpu_ids: GPU_IDS_TYPE = "",
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class Refine3DJob(_Relion5Job):
    """3D auto-refinement of pre-aligned particles."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.refine3d"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        if "helical_twist_range" in kwargs:
            (
                kwargs["helical_twist_min"],
                kwargs["helical_twist_max"],
                kwargs["helical_twist_inistep"],
            ) = kwargs.pop("helical_twist_range")
        if "helical_rise_range" in kwargs:
            (
                kwargs["helical_rise_min"],
                kwargs["helical_rise_max"],
                kwargs["helical_rise_inistep"],
            ) = kwargs.pop("helical_rise_range")
        if "rot_tilt_psi_range" in kwargs:
            kwargs["range_rot"], kwargs["range_tilt"], kwargs["range_psi"] = kwargs.pop(
                "rot_tilt_psi_range"
            )
        if "helical_tube_diameter_range" in kwargs:
            (
                kwargs["helical_tube_inner_diameter"],
                kwargs["helical_tube_outer_diameter"],
            ) = kwargs.pop("helical_tube_diameter_range")
        if "offset_range_step" in kwargs:
            kwargs["offset_range"], kwargs["offset_step"] = kwargs.pop(
                "offset_range_step"
            )
        kwargs["fn_cont"] = ""
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs["helical_twist_range"] = (
            kwargs.pop("helical_twist_min", 0),
            kwargs.pop("helical_twist_max", 0),
            kwargs.pop("helical_twist_inistep", 0),
        )
        kwargs["helical_rise_range"] = (
            kwargs.pop("helical_rise_min", 0),
            kwargs.pop("helical_rise_max", 0),
            kwargs.pop("helical_rise_inistep", 0),
        )
        kwargs["rot_tilt_psi_range"] = (
            kwargs.pop("range_rot", -1),
            kwargs.pop("range_tilt", 15),
            kwargs.pop("range_psi", 10),
        )
        kwargs["helical_tube_diameter_range"] = (
            kwargs.pop("helical_tube_inner_diameter", -1),
            kwargs.pop("helical_tube_outer_diameter", -1),
        )
        kwargs["offset_range_step"] = (
            kwargs.pop("offset_range", 5),
            kwargs.pop("offset_step", 1),
        )
        kwargs.pop("fn_cont", None)
        return super().normalize_kwargs_inv(**kwargs)

    def run(
        self,
        fn_img: IN_PARTICLES = "",
        fn_ref: REF_TYPE = "",
        fn_mask: MASK_TYPE = "",
        # Reference
        ref_correct_greyscale: REF_CORRECT_GRAY_TYPE = False,
        trust_ref_size: TRUST_REF_SIZE_TYPE = True,
        ini_high: INITIAL_LOWPASS_TYPE = 60,
        sym_name: REF_SYMMETRY_TYPE = "C1",
        # CTF
        do_ctf_correction: DO_CTF_TYPE = True,
        ctf_intact_first_peak: IGNORE_CTF_TYPE = False,
        # Optimisation
        particle_diameter: MASK_DIAMETER_TYPE = 200,
        do_zero_mask: MASK_WITH_ZEROS_TYPE = True,
        do_solvent_fsc: SOLVENT_FLATTEN_FSC_TYPE = False,
        do_blush: DO_BLUSH_TYPE = False,
        # Sampling
        sampling: ANG_SAMPLING_TYPE = "7.5 degrees",
        offset_range_step: OFFSET_RANGE_STEP_TYPE = (5, 1),
        auto_local_sampling: LOC_ANG_SAMPLING_TYPE = "1.8 degrees",
        relax_sym: RELAX_SYMMETRY_TYPE = "",
        auto_faster: Annotated[
            bool, {"label": "Use finer angular sampling faster", "group": "Sampling"}
        ] = False,
        # Helix
        do_helix: DO_HELIX_TYPE = False,
        helical_tube_diameter_range: HELICAL_TUBE_DIAMETER_RANGE_TYPE = (-1, -1),
        rot_tilt_psi_range: ROT_TILT_PSI_RANGE_TYPE = (-1, 15, 10),
        helical_range_distance: HELICAL_RANGE_DIST_TYPE = -1,
        do_apply_helical_symmetry: DO_APPLY_HELICAL_SYMMETRY_TYPE = True,
        helical_nr_asu: HELICAL_NR_ASU_TYPE = 1,
        helical_twist_initial: HELICAL_TWIST_INITIAL_TYPE = 0,
        helical_rise_initial: HELICAL_RISE_INITIAL_TYPE = 0,
        helical_z_percentage: HELICAL_Z_PERCENTAGE_TYPE = 30,
        keep_tilt_prior_fixed: KEEP_TILT_PRIOR_FIXED_TYPE = True,
        do_local_search_helical_symmetry: DO_LOCAL_SEARCH_HELICAL_SYMMETRY_TYPE = False,
        helical_twist_range: HELICAL_TWIST_RANGE_TYPE = (0, 0, 0),
        helical_rise_range: HELICAL_RISE_RANGE_TYPE = (0, 0, 0),
        # Compute
        do_parallel_discio: USE_PARALLEL_DISC_IO_TYPE = True,
        nr_pool: NUM_POOL_TYPE = 3,
        use_scratch: USE_SCRATCH_TYPE = False,
        do_pad1: Annotated[bool, {"label": "Skip padding", "group": "Compute"}] = False,
        do_preread_images: DO_PREREAD_TYPE = False,
        do_combine_thru_disc: DO_COMBINE_THRU_DISC_TYPE = False,
        gpu_ids: GPU_IDS_TYPE = "",
        # Running
        nr_mpi: MPI_TYPE = 3,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_ctf_correction"].changed.connect
        def _on_do_ctf_correction_changed(value: bool):
            widgets["ctf_intact_first_peak"].enabled = value

        widgets["ctf_intact_first_peak"].enabled = widgets["do_ctf_correction"].value
        _setup_helix_params(widgets)


def _setup_helix_params(widgets: dict[str, ValueWidget]) -> None:
    helical_names = [
        "helical_tube_diameter_range",
        "rot_tilt_psi_range",
        "do_apply_helical_symmetry",
        "do_local_search_helical_symmetry",
        "helical_range_distance",
        "helical_twist_initial",
        "helical_twist_range",
        "helical_rise_initial",
        "helical_rise_range",
        "helical_nr_asu",
        "helical_z_percentage",
        "keep_tilt_prior_fixed",
    ]

    @widgets["do_helix"].changed.connect
    def _on_helical(value: bool):
        for name in helical_names:
            widgets[name].enabled = value
        _on_do_local_search_helical_symmetry(
            widgets["do_local_search_helical_symmetry"].value
        )

    for name in helical_names:
        widgets[name].enabled = False

    @widgets["do_local_search_helical_symmetry"].changed.connect
    def _on_do_local_search_helical_symmetry(value: bool):
        widgets["helical_twist_range"].enabled = value
        widgets["helical_rise_range"].enabled = value

    widgets["helical_twist_range"].enabled = False
    widgets["helical_rise_range"].enabled = False


class _SelectJob(_Relion5Job):
    @classmethod
    def type_label(cls):
        return "relion.select"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        for name, default in [
            ("fn_model", ""),
            ("fn_mic", ""),
            ("fn_data", ""),
            ("do_class_ranker", False),
            ("do_discard", False),
            ("do_filaments", False),
            ("do_queue", False),
            ("do_random", False),
            ("do_recenter", False),
            ("do_regroup", False),
            ("do_select_values", False),
            ("do_split", False),
            ("do_remove_duplicates", False),
            ("select_label", "rlnCtfMaxResolution"),
            ("select_minval", -9999.0),
            ("select_maxval", 9999.0),
            ("duplicate_threshold", 30.0),
            ("image_angpix", -1.0),
            ("rank_threshold", 0.5),
            ("select_nr_classes", -1),
            ("select_nr_parts", -1),
            ("nr_groups", 1),
            ("split_size", 100),
            ("nr_split", -1),
            ("dendrogram_threshold", 0.85),
            ("dendrogram_minclass", -1000),
            ("min_dedicated", 1),
        ]:
            kwargs.setdefault(name, default)
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        params = cls._signature().parameters
        for name in list(kwargs.keys()):
            if name not in params:
                kwargs.pop(name)
        return kwargs


class SelectClassesInteractiveJob(_SelectJob):
    @classmethod
    def type_label(cls):
        return "relion.select.interactive"

    def run(self, fn_model: IN_OPTIMISER = ""):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def _search_parent_class3d(cls, path: Path) -> JobDirectory | None:
        job = JobDirectory(path)
        for p in job.parent_jobs():
            if p.job_type_label() == "relion.class3d":
                return p
        else:
            return None

    @classmethod
    def _search_opt(cls, path: Path) -> str | None:
        """Only used for inspect particles of tomo extension."""
        if job_class3d := cls._search_parent_class3d(path):
            params = job_class3d.get_job_params_as_dict()
            if opt_path := params.get("in_opimisation", None):
                return opt_path
        return None

    @classmethod
    def _search_mics(cls, path: Path) -> str | None:
        """Only used for inspect particles of tomo extension."""
        if job_class3d := cls._search_parent_class3d(path):
            params = job_class3d.get_job_params_as_dict()
            if opt_path := params.get("in_opimisation", None):
                opt_path = job_class3d.relion_project_dir / opt_path
                opt = OptimisationSetModel.validate_file(opt_path)
                return opt.tomogram_star
            elif in_tomo := params.get("in_tomograms", None):
                return in_tomo
        return None


class SelectClassesAutoJob(_SelectJob):
    @classmethod
    def type_label(cls):
        return "relion.select.class2dauto"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_class_ranker"] = True
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        fn_model: IN_OPTIMISER = "",
        rank_threshold: Annotated[
            float, {"label": "Minimum threshold for auto selection"}
        ] = 0.5,
        select_nr_parts: Annotated[
            int, {"label": "Minimum number of particles to select"}
        ] = -1,
        select_nr_classes: Annotated[
            int, {"label": "Or minimum number of classes to select"}
        ] = -1,
        do_recenter: Annotated[bool, {"label": "Recenter the class averages"}] = False,
        do_regroup: Annotated[bool, {"label": "Regroup the particles"}] = False,
        nr_groups: Annotated[int, {"label": "Approximate number of groups"}] = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class _SelectValuesJob(_SelectJob):
    @classmethod
    def type_label(cls):
        return "relion.select.onvalue"


class SelectParticlesJob(_SelectValuesJob):
    @classmethod
    def command_id(cls):
        return super().command_id() + "-particles"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_select_values"] = True
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        fn_data: IN_PARTICLES = "",
        select_label: Annotated[
            str, {"label": "Metadata label for selection"}
        ] = "rlnCtfMaxResolution",
        select_minval: Annotated[
            float, {"label": "Minimum value for selection"}
        ] = -9999,
        select_maxval: Annotated[
            float, {"label": "Maximum value for selection"}
        ] = 9999,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class SelectMicrographsJob(_SelectValuesJob):
    @classmethod
    def command_id(cls):
        return super().command_id() + "-micrographs"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_discard"] = True
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        fn_mic: IN_MICROGRAPHS = "",
        select_label: Annotated[
            str, {"label": "Metadata label for selection"}
        ] = "rlnCtfMaxResolution",
        select_minval: Annotated[
            float, {"label": "Minimum value for selection"}
        ] = -9999,
        select_maxval: Annotated[
            float, {"label": "Maximum value for selection"}
        ] = 9999,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class SelectRemoveDuplicatesJob(_SelectJob):
    """Remove duplicate particles based on their coordinates."""

    @classmethod
    def type_label(cls):
        return "relion.select.removeduplicates"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_remove_duplicates"] = True
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        fn_data: IN_PARTICLES = "",
        duplicate_threshold: Annotated[
            float, {"label": "Minimum inter-particle distance (A)"}
        ] = 30,
        image_angpix: Annotated[float, {"label": "Image pixel size (A)"}] = -1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class SelectSplitJob(_SelectJob):
    """Split particles into subsets."""

    @classmethod
    def type_label(cls):
        return "relion.select.split"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_split"] = True
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        fn_data: IN_PARTICLES = "",
        do_random: Annotated[
            bool, {"label": "Randomise order before making subsets"}
        ] = False,
        split_size: Annotated[int, {"label": "Number of particles per subset"}] = 100,
        nr_split: Annotated[int, {"label": "Or number of subsets"}] = -1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class SelectFilamentsJob(_SelectJob):
    @classmethod
    def type_label(cls):
        return "relion.select.filamentsdendrogram"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_filaments"] = True
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        fn_model: IN_OPTIMISER = "",
        dendrogram_threshold: Annotated[
            float, {"label": "Dendrogram threshold"}
        ] = 0.85,
        dendrogram_minclass: Annotated[int, {"label": "Minimum class size"}] = -1000,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class MaskCreationJob(_Relion5Job):
    """Create a 3D mask from a reconstructed map."""

    @classmethod
    def type_label(cls) -> str:
        return "relion.maskcreate"

    def run(
        self,
        fn_in: MAP_TYPE = "",
        lowpass_filter: Annotated[
            float, {"label": "Lowpass filter (A)", "group": "Mask"}
        ] = 15,
        angpix: Annotated[float, {"label": "Pixel size (A)", "group": "Mask"}] = -1,
        inimask_threshold: Annotated[
            float, {"label": "Initial binarisation threshold", "group": "Mask"}
        ] = 0.02,
        extend_inimask: Annotated[
            int, {"label": "Extend binary map (pixels)", "group": "Mask"}
        ] = 3,
        width_mask_edge: Annotated[
            int, {"label": "Soft edge (pixels)", "group": "Mask"}
        ] = 3,
        do_helix: DO_HELIX_TYPE = False,
        helical_z_percentage: HELICAL_Z_PERCENTAGE_TYPE = 30,
        # Running
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class PostProcessJob(_Relion5Job):
    @classmethod
    def type_label(cls) -> str:
        return "relion.postprocess"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs(**kwargs)
        b_factor = kwargs.pop("b_factor", {})
        assert isinstance(b_factor, dict), f"b_factor must be a dict, got {b_factor!r}"
        kwargs["do_auto_bfac"] = b_factor.get("do_auto_bfac", True)
        kwargs["autob_lowres"] = b_factor.get("autob_lowres", 10)
        kwargs["do_adhoc_bfac"] = b_factor.get("do_adhoc_bfac", False)
        kwargs["adhoc_bfac"] = b_factor.get("adhoc_bfac", -1000)
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        do_auto_bfac = kwargs.pop("do_auto_bfac", True)
        autob_lowres = kwargs.pop("autob_lowres", 10)
        do_adhoc_bfac = kwargs.pop("do_adhoc_bfac", False)
        adhoc_bfac = kwargs.pop("adhoc_bfac", -1000)
        kwargs["b_factor"] = {
            "do_auto_bfac": parse_string(do_auto_bfac, bool),
            "autob_lowres": parse_string(autob_lowres, float),
            "do_adhoc_bfac": parse_string(do_adhoc_bfac, bool),
            "adhoc_bfac": parse_string(adhoc_bfac, float),
        }
        return kwargs

    def run(
        self,
        # I/O
        fn_in: HALFMAP_TYPE = "",
        fn_mask: MASK_TYPE = "",
        angpix: Annotated[
            float, {"label": "Calibrated pixel size (A)", "group": "I/O"}
        ] = -1,
        # Sharpen
        b_factor: B_FACTOR_TYPE = None,
        do_skip_fsc_weighting: Annotated[
            bool, {"label": "Skip FSC-weighting", "group": "Sharpen"}
        ] = False,
        low_pass: Annotated[
            float, {"label": "Low-pass filter (A)", "group": "Sharpen"}
        ] = 5,
        fn_mtf: Annotated[
            str, {"label": "MTF of the detector", "group": "Sharpen"}
        ] = "",
        mtf_angpix: Annotated[
            float, {"label": "MTF pixel size (A)", "group": "Sharpen"}
        ] = 1,
        # Running
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


FIT_CTF_CHOICES = Literal["No", "Per-micrograph", "Per-particle"]


class CtfRefineJob(_Relion5Job):
    _do_ctf_args = ("do_defocus", "do_astig", "do_bfactor", "do_phase")

    @classmethod
    def type_label(cls) -> str:
        return "relion.ctfrefine"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_ctf"] = any(kwargs[name] != "No" for name in cls._do_ctf_args)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        do_ctf = kwargs.pop("do_ctf", False)
        if not do_ctf:
            for name in cls._do_ctf_args:
                kwargs[name] = "No"
        return kwargs

    def run(
        self,
        fn_data: IN_PARTICLES = "",
        fn_post: PROCESS_TYPE = "",
        # Fit
        do_aniso_mag: Annotated[
            bool, {"label": "Estimate anisotropic magnification", "group": "Fit"}
        ] = False,
        do_defocus: Annotated[
            FIT_CTF_CHOICES, {"label": "Fit defocus", "group": "Fit"}
        ] = "No",
        do_astig: Annotated[
            FIT_CTF_CHOICES, {"label": "Fit astigmatism", "group": "Fit"}
        ] = "No",
        do_bfactor: Annotated[
            FIT_CTF_CHOICES, {"label": "Fit B-factor", "group": "Fit"}
        ] = "No",
        do_phase: Annotated[
            FIT_CTF_CHOICES, {"label": "Fit phase shift", "group": "Fit"}
        ] = "No",
        do_tilt: Annotated[
            bool, {"label": "Estimate beam tilt", "group": "Fit"}
        ] = False,
        do_trefoil: Annotated[
            bool, {"label": "Estimate trefoil", "group": "Fit"}
        ] = False,
        do_4thorder: Annotated[
            bool, {"label": "Estimate 4th order aberrations", "group": "Fit"}
        ] = False,
        minres: Annotated[
            float, {"label": "Minimum resolution for fitting (A)", "group": "Fit"}
        ] = 30,
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["do_aniso_mag"].changed.connect
        def _on_do_aniso_mag_changed(value: bool):
            for name in cls._do_ctf_args:
                widgets[name].enabled = not value

        _on_do_aniso_mag_changed(widgets["do_aniso_mag"].value)
