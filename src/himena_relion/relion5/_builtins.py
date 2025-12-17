from typing import Annotated, Any

from himena_relion._job_class import _RelionBuiltinJob, connect_jobs
from himena_relion import _configs

# I/O

IN_OPT_TYPE = Annotated[str, {"label": "3D Refinement", "group": "I/O"}]
USE_DIRECT_TYPE = Annotated[bool, {"label": "Use direct entries", "group": "I/O"}]
IN_PARTS_TYPE = Annotated[str, {"label": "Particles", "group": "I/O"}]
IN_TOMO_TYPE = Annotated[str, {"label": "Tomograms", "group": "I/O"}]
IN_TRAJ_TYPE = Annotated[str, {"label": "Trajectories", "group": "I/O"}]
REF_TYPE = Annotated[str, {"label": "Reference map", "group": "I/O"}]
MASK_TYPE = Annotated[str, {"label": "Reference mask", "group": "I/O"}]
CONTINUE_TYPE = Annotated[str, {"label": "Continue from here", "group": "I/O"}]

# others
USE_GPU_TYPE = Annotated[bool, {"label": "Use GPU acceleration", "group": "Compute"}]
GPU_IDS_TYPE = Annotated[str, {"label": "GPU IDs", "group": "Compute"}]
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


class _MotionCorrJobBase(_RelionBuiltinJob):
    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_motioncor2_exe"] = _configs.get_motioncor2_exe()
        kwargs["patch_x"], kwargs["patch_y"] = kwargs["patch"]
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
        input_star_mics: Annotated[str, {"label": "Micrographs", "group": "I/O"}] = "",
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
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_own_motioncor"] = True
        kwargs["other_motioncor2_args"] = ""
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs):
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("do_own_motioncor", None)
        kwargs.pop("other_motioncor2_args", None)
        return kwargs

    def run(
        self,
        input_star_mics: Annotated[str, {"label": "Micrographs", "group": "I/O"}] = "",
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
            int, {"label": "... every n frames", "group": "I/O"}
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
        min_dedicated: MIN_DEDICATED_TYPE = 1,
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class CtfEstimationJob(_RelionBuiltinJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.ctffind.ctffind4"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_ctffind_exe"] = _configs.get_ctffind4_exe()
        kwargs["phase_min"], kwargs["phase_max"], kwargs["phase_step"] = kwargs.pop(
            "phase_range"
        )
        kwargs["dfmin"], kwargs["dfmax"], kwargs["dfstep"] = kwargs.pop("dfrange")
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("fn_ctffind_exe", None)
        kwargs["phase_range"] = (
            kwargs.pop("phase_min"),
            kwargs.pop("phase_max"),
            kwargs.pop("phase_step"),
        )
        kwargs["dfrange"] = (
            kwargs.pop("dfmin"),
            kwargs.pop("dfmax"),
            kwargs.pop("dfstep"),
        )
        return super().normalize_kwargs_inv(**kwargs)

    def run(
        self,
        input_star_mics: Annotated[str, {"label": "Micrographs", "group": "I/O"}] = "",
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
        min_dedicated: MIN_DEDICATED_TYPE = 1,
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


connect_jobs(
    MotionCorr2Job,
    CtfEstimationJob,
    node_mapping={"corrected_micrographs.star": "input_star_mics"},
)
