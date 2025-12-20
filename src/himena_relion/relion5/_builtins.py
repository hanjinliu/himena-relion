from typing import Annotated, Any

from himena_relion._job_class import _RelionBuiltinJob, connect_jobs, parse_string
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
    bool, {"label": "Resize reference if needed", "group": "Compute"}
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
SIGMA_TILT_TYPE = Annotated[
    float, {"label": "Prior width on tilt angle", "group": "Optimisation"}
]
DO_BLUSH_TYPE = Annotated[
    bool, {"label": "Use Blush regularisation", "group": "Optimisation"}
]
# Sampling
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
    bool, {"label": "Keep tilt-prior fixed", "group": "Sampling"}
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
    bool, {"label": "Use parallel disc I/O", "group": "Running"}
]
NUM_POOL_TYPE = Annotated[
    int, {"label": "Number of pooled particles", "min": 1, "group": "Running"}
]
DO_PREREAD_TYPE = Annotated[
    bool, {"label": "Pre-read all particles into RAM", "group": "Compute"}
]
DO_COMBINE_THRU_DISC_TYPE = Annotated[
    bool, {"label": "Combine iterations through disc", "group": "Running"}
]
USE_GPU_TYPE = Annotated[bool, {"label": "Use GPU acceleration", "group": "Compute"}]
GPU_IDS_TYPE = Annotated[str, {"label": "GPU IDs", "group": "Compute"}]
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


class CtfEstimationJob(_Relion5Job):
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
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class Class3DJob(_Relion5Job):
    @classmethod
    def type_label(cls) -> str:
        return "relion.class3d"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["scratch_dir"] = _configs.get_scratch_dir()
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
            kwargs.pop("rot_range", -1),
            kwargs.pop("tilt_range", 15),
            kwargs.pop("psi_range", 10),
        )
        kwargs["helical_tube_diameter_range"] = (
            kwargs.pop("helical_tube_inner_diameter", -1),
            kwargs.pop("helical_tube_outer_diameter", -1),
        )
        kwargs["offset_range_step"] = (
            kwargs.pop("offset_range", 5),
            kwargs.pop("offset_step", 1),
        )
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
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
            kwargs["rot_range"], kwargs["tilt_range"], kwargs["psi_range"] = kwargs.pop(
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
        return super().normalize_kwargs_inv(**kwargs)

    def run(
        self,
        fn_img: IMG_TYPE = "",
        fn_ref: REF_TYPE = "",
        fn_mask: MASK_TYPE = "",
        fn_cont: CONTINUE_TYPE = "",
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
        keep_tilt_prior_fixed: KEEP_TILT_PRIOR_FIXED_TYPE = True,
        # Helix
        do_helix: DO_HELIX_TYPE = False,
        helical_tube_diameter_range: HELICAL_TUBE_DIAMETER_RANGE_TYPE = (-1, -1),
        rot_tilt_psi_range: ROT_TILT_PSI_RANGE_TYPE = (-1, 15, 10),
        do_apply_helical_symmetry: DO_APPLY_HELICAL_SYMMETRY_TYPE = True,
        do_local_search_helical_symmetry: DO_LOCAL_SEARCH_HELICAL_SYMMETRY_TYPE = False,
        helical_range_distance: HELICAL_RANGE_DIST_TYPE = -1,
        helical_twist_initial: HELICAL_TWIST_INITIAL_TYPE = 0,
        helical_twist_range: HELICAL_TWIST_RANGE_TYPE = (0, 0, 0),
        helical_rise_initial: HELICAL_RISE_INITIAL_TYPE = 0,
        helical_rise_range: HELICAL_RISE_RANGE_TYPE = (0, 0, 0),
        helical_nr_asu: HELICAL_NR_ASU_TYPE = 1,
        helical_z_percentage: HELICAL_Z_PERCENTAGE_TYPE = 30,
        # Compute
        do_fast_subsets: Annotated[
            bool, {"label": "Use fast subsets", "group": "Compute"}
        ] = False,
        do_parallel_discio: USE_PARALLEL_DISC_IO_TYPE = True,
        nr_pool: NUM_POOL_TYPE = 3,
        do_pad1: Annotated[bool, {"label": "Skip padding", "group": "Compute"}] = False,
        do_preread_images: DO_PREREAD_TYPE = False,
        do_combine_thru_disc: DO_COMBINE_THRU_DISC_TYPE = False,
        use_gpu: USE_GPU_TYPE = False,
        gpu_ids: GPU_IDS_TYPE = "",
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class Refine3DJob(_Relion5Job):
    @classmethod
    def type_label(cls) -> str:
        return "relion.refine3d"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["scratch_dir"] = _configs.get_scratch_dir()
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
            kwargs.pop("rot_range", -1),
            kwargs.pop("tilt_range", 15),
            kwargs.pop("psi_range", 10),
        )
        kwargs["helical_tube_diameter_range"] = (
            kwargs.pop("helical_tube_inner_diameter", -1),
            kwargs.pop("helical_tube_outer_diameter", -1),
        )
        kwargs["offset_range_step"] = (
            kwargs.pop("offset_range", 5),
            kwargs.pop("offset_step", 1),
        )
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
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
            kwargs["rot_range"], kwargs["tilt_range"], kwargs["psi_range"] = kwargs.pop(
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
        return super().normalize_kwargs_inv(**kwargs)

    def run(
        self,
        fn_img: IMG_TYPE = "",
        fn_ref: REF_TYPE = "",
        fn_mask: MASK_TYPE = "",
        fn_cont: CONTINUE_TYPE = "",
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
        do_solvent_fsc: Annotated[
            bool, {"label": "Use solvent-flattened FSCs", "group": "Compute"}
        ] = False,
        do_blush: DO_BLUSH_TYPE = False,
        # Sampling
        sampling: ANG_SAMPLING_TYPE = "7.5 degrees",
        offset_range_step: OFFSET_RANGE_STEP_TYPE = (5, 1),
        auto_local_sampling: LOC_ANG_SAMPLING_TYPE = "1.8 degrees",
        relax_sym: RELAX_SYMMETRY_TYPE = "",
        sigma_tilt: SIGMA_TILT_TYPE = -1,
        keep_tilt_prior_fixed: KEEP_TILT_PRIOR_FIXED_TYPE = True,
        # Helix
        do_helix: DO_HELIX_TYPE = False,
        do_apply_helical_symmetry: DO_APPLY_HELICAL_SYMMETRY_TYPE = True,
        helical_nr_asu: HELICAL_NR_ASU_TYPE = 1,
        helical_twist_initial: HELICAL_TWIST_INITIAL_TYPE = 0,
        helical_rise_initial: HELICAL_RISE_INITIAL_TYPE = 0,
        helical_z_percentage: HELICAL_Z_PERCENTAGE_TYPE = 30,
        helical_tube_diameter_range: HELICAL_TUBE_DIAMETER_RANGE_TYPE = (-1, -1),
        rot_tilt_psi_range: ROT_TILT_PSI_RANGE_TYPE = (-1, 15, 10),
        do_local_search_helical_symmetry: DO_LOCAL_SEARCH_HELICAL_SYMMETRY_TYPE = False,
        helical_twist_range: HELICAL_TWIST_RANGE_TYPE = (0, 0, 0),
        helical_rise_range: HELICAL_RISE_RANGE_TYPE = (0, 0, 0),
        helical_range_distance: HELICAL_RANGE_DIST_TYPE = -1,
        # Compute
        do_parallel_discio: USE_PARALLEL_DISC_IO_TYPE = True,
        nr_pool: NUM_POOL_TYPE = 3,
        do_pad1: Annotated[bool, {"label": "Skip padding", "group": "Compute"}] = False,
        do_preread_images: DO_PREREAD_TYPE = False,
        do_combine_thru_disc: DO_COMBINE_THRU_DISC_TYPE = False,
        use_gpu: USE_GPU_TYPE = False,
        gpu_ids: GPU_IDS_TYPE = "",
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


# TODO: SelectInteractive
# TODO: SelectRemoveDuplicates


class MaskCreationJob(_Relion5Job):
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


class PostProcessingJob(_Relion5Job):
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


connect_jobs(
    MotionCorr2Job,
    CtfEstimationJob,
    node_mapping={"corrected_micrographs.star": "input_star_mics"},
)
connect_jobs(
    Refine3DJob,
    MaskCreationJob,
    node_mapping={"run_class001.mrc": "fn_in"},
)
connect_jobs(
    Refine3DJob,
    PostProcessingJob,
    node_mapping={"run_half1_class001_unfil.mrc": "fn_in"},
)
