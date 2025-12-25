from typing import Annotated, Any

from magicgui.widgets.bases import ValueWidget
from himena_relion._job_class import _RelionBuiltinJob, parse_string
from himena_relion._widgets._magicgui import PathDrop, BfactorEdit
from himena_relion import _configs


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
        "type_label": "MicrographsData",
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
        "type_label": "DensityMap.mrc.halfmap",
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

# CTF
DO_CTF_TYPE = Annotated[bool, {"label": "Do CTF correction", "group": "CTF"}]
IGNORE_CTF_TYPE = Annotated[
    bool, {"label": "Ignore CTFs until first peak", "group": "CTF"}
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
SIGMA_TILT_TYPE = Annotated[
    float, {"label": "Prior width on tilt angle", "group": "Sampling"}
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
        eer_grouping: Annotated[
            int, {"label": "EER fractionation", "min": 1, "group": "I/O"}
        ] = 32,
        do_even_odd_split: Annotated[
            bool, {"label": "Save images for denoising", "group": "I/O"}
        ] = False,
        bfactor: Annotated[
            float, {"label": "Bfactor", "group": "Motion Correction"}
        ] = 150,
        group_frames: Annotated[
            int, {"label": "Group frames", "min": 1, "group": "Motion Correction"}
        ] = 1,
        bin_factor: Annotated[
            int, {"label": "Binning factor", "min": 1, "group": "Motion Correction"}
        ] = 1,
        fn_defect: Annotated[
            str, {"label": "Defect file", "group": "Motion Correction"}
        ] = "",
        fn_gain_ref: Annotated[
            str, {"label": "Gain reference image", "group": "Motion Correction"}
        ] = "",
        gain_rot: Annotated[
            str,
            {
                "choices": [
                    "No rotation (0)",
                    "90 degrees (1)",
                    "180 degrees (2)",
                    "270 degrees (3)",
                ],
                "label": "Gain reference rotation",
                "group": "Motion Correction",
            },
        ] = "No rotation (0)",
        gain_flip: Annotated[
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
        ] = "No flipping (0)",
        other_motioncor2_args: Annotated[
            str, {"label": "Other MotionCor2 arguments", "group": "Motion Correction"}
        ] = "",
        patch: Annotated[
            tuple[int, int],
            {"label": "Number of patches (X, Y)", "group": "Motion Correction"},
        ] = (1, 1),
        gpu_ids: GPU_IDS_TYPE = "0",
        # Running
        min_dedicated: MIN_DEDICATED_TYPE = 1,
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
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
        do_even_odd_split: Annotated[
            bool, {"label": "Save images for denoising", "group": "I/O"}
        ] = False,
        do_float16: Annotated[
            bool, {"label": "Output in float16", "group": "I/O"}
        ] = True,
        eer_grouping: Annotated[
            int, {"label": "EER fractionation", "min": 1, "group": "I/O"}
        ] = 32,
        do_save_ps: Annotated[
            bool, {"label": "Save sum of power spectra", "group": "I/O"}
        ] = True,
        group_for_ps: Annotated[
            int, {"label": "Save power spectra every n frames", "group": "I/O"}
        ] = 4,
        bfactor: Annotated[
            float, {"label": "Bfactor", "group": "Motion Correction"}
        ] = 150,
        group_frames: Annotated[
            int, {"label": "Group frames", "min": 1, "group": "Motion Correction"}
        ] = 1,
        bin_factor: Annotated[
            int, {"label": "Binning factor", "min": 1, "group": "Motion Correction"}
        ] = 1,
        fn_defect: Annotated[
            str, {"label": "Defect file", "group": "Motion Correction"}
        ] = "",
        fn_gain_ref: Annotated[
            str, {"label": "Gain reference image", "group": "Motion Correction"}
        ] = "",
        gain_rot: Annotated[
            str,
            {
                "choices": [
                    "No rotation (0)",
                    "90 degrees (1)",
                    "180 degrees (2)",
                    "270 degrees (3)",
                ],
                "label": "Gain reference rotation",
                "group": "Motion Correction",
            },
        ] = "No rotation (0)",
        gain_flip: Annotated[
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
        ] = "No flipping (0)",
        patch: Annotated[
            tuple[int, int],
            {"label": "Number of patches (X, Y)", "group": "Motion Correction"},
        ] = (1, 1),
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
        input_star_mics: IN_MICROGRAPHS = "",
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
        localsearch_nominal_defocus: Annotated[
            float, {"label": "Nominal defocus search range", "group": "CTFFIND"}
        ] = 10000,
        exp_factor_dose: Annotated[
            float,
            {"label": "Dose-dependent Thon ring fading (e/A^2)", "group": "CTFFIND"},
        ] = 100,
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


class Class3DJob(_Relion5Job):
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

    def run(
        self,
        fn_img: IMG_TYPE = "",
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
        highres_limit: Annotated[
            float, {"label": "High-resolution limit (A)", "group": "Optimisation"}
        ] = -1,
        do_blush: DO_BLUSH_TYPE = False,
        # Sampling
        dont_skip_align: Annotated[
            bool, {"label": "Perform image alignment", "group": "Sampling"}
        ] = True,
        sampling: ANG_SAMPLING_TYPE = "7.5 degrees",
        offset_range_step: OFFSET_RANGE_STEP_TYPE = (5, 1),
        allow_coarser: Annotated[
            bool, {"label": "Allow coarser sampling", "group": "Sampling"}
        ] = False,
        do_local_ang_searches: Annotated[
            bool, {"label": "Perform local angular searches", "group": "Sampling"}
        ] = False,
        sigma_angles: Annotated[
            float, {"label": "Local angular search range", "group": "Sampling"}
        ] = 5,
        relax_sym: RELAX_SYMMETRY_TYPE = "",
        sigma_tilt: SIGMA_TILT_TYPE = -1,
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

    @classmethod
    def setup_widgets(self, widgets):
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
        fn_img: IMG_TYPE = "",
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
        sigma_tilt: SIGMA_TILT_TYPE = -1,
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
    def setup_widgets(self, widgets):
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
        b_factor = kwargs.get("b_factor", {})
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
