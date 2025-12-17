from typing import Annotated, Any

import pandas as pd
from himena_relion.consts import JOB_ID_MAP
from himena_relion._job_class import RelionJob, connect_jobs, to_string
from himena_relion import _configs

TILTSERIES_TYPE = Annotated[str, {"label": "Tilt series", "group": "I/O"}]
GPU_IDS_TYPE = Annotated[str, {"label": "GPU IDs", "group": "Running"}]
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


class _RelionBuiltinJob(RelionJob):
    @classmethod
    def command_id(cls) -> str:
        return cls.type_label()

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        """Normalize the keyword arguments for this job."""
        kwargs.update(_configs.get_queue_dict())
        return kwargs

    @classmethod
    def job_title(cls) -> str:
        return JOB_ID_MAP.get(cls.type_label(), "Unknown")

    @classmethod
    def himena_model_type(cls):
        return cls.type_label()

    @classmethod
    def prep_job_star(cls, **kwargs):
        return prep_builtin_job_star(
            type_label=cls.type_label(),
            kwargs=cls.normalize_kwargs(**kwargs),
        )


def prep_builtin_job_star(
    type_label: str, is_tomo: int = 0, kwargs: dict[str, Any] = {}
):
    job = {
        "rlnJobTypeLabel": type_label,
        "rlnJobIsContinue": 0,
        "rlnJobIsTomo": is_tomo,
    }
    _var = []
    _val = []
    for k, v in kwargs.items():
        _var.append(k)
        _val.append(to_string(v))
    joboptions_values = {
        "rlnJobOptionVariable": _var,
        "rlnJobOptionValue": _val,
    }
    return {
        "job": job,
        "joboptions_values": pd.DataFrame(joboptions_values),
    }


class _MotionCorrJobBase(_RelionBuiltinJob):
    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_motioncor2_exe"] = _configs.get_motioncor2_exe()
        return super().normalize_kwargs(**kwargs)


class MotionCorr2Job(_MotionCorrJobBase):
    @classmethod
    def type_label(cls) -> str:
        return "relion.motioncorr.motioncor2"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_own_motioncor"] = False
        kwargs["do_save_ps"] = False
        return super().normalize_kwargs(**kwargs)

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
        patch_x: Annotated[
            int, {"label": "Number of patches X", "group": "Motion Correction"}
        ] = 1,
        patch_y: Annotated[
            int, {"label": "Number of patches Y", "group": "Motion Correction"}
        ] = 1,
        gpu_ids: GPU_IDS_TYPE = "0",
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
        patch_x: Annotated[
            int, {"label": "Number of patches X", "group": "Motion Correction"}
        ] = 1,
        patch_y: Annotated[
            int, {"label": "Number of patches Y", "group": "Motion Correction"}
        ] = 1,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class _AlignTiltSeriesJobBase(_RelionBuiltinJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.aligntiltseries"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_aretomo_exe"] = _configs.get_aretomo2_exe()
        kwargs["fn_batchtomo_exe"] = _configs.get_batchruntomo_exe()
        return super().normalize_kwargs(**kwargs)


class CtfEstimationJob(_RelionBuiltinJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.ctffind.ctffind4"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_ctffind_exe"] = _configs.get_ctffind4_exe()
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        input_star_mics: Annotated[str, {"label": "Micrographs", "group": "I/O"}] = "",
        do_phaseshift: Annotated[
            bool, {"label": "Estimate phase shifts", "group": "I/O"}
        ] = False,
        phase_min: Annotated[
            float, {"label": "Phase shift min (deg)", "group": "I/O"}
        ] = 0,
        phase_max: Annotated[
            float, {"label": "Phase shift max (deg)", "group": "I/O"}
        ] = 180,
        phase_step: Annotated[
            float, {"label": "Phase shift step (deg)", "group": "I/O"}
        ] = 10,
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
        dfmin: Annotated[int, {"label": "Defocus min (A)", "group": "CTFFIND"}] = 5000,
        dfmax: Annotated[int, {"label": "Defocus max (A)", "group": "CTFFIND"}] = 50000,
        dfstep: Annotated[int, {"label": "Defocus step (A)", "group": "CTFFIND"}] = 500,
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


# TODO: class ExcludeTiltJob(_RelionBuiltinJob):


class AlignTiltSeriesImodFiducial(_AlignTiltSeriesJobBase):
    @classmethod
    def command_id(cls):
        return super().command_id() + "-imodfiducial"

    @classmethod
    def job_title(cls) -> str:
        return "Align Tilt Series (IMOD Fiducials)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_imod_fiducials"] = True
        kwargs["do_aretomo2"] = False
        kwargs["do_imod_patchtrack"] = False
        kwargs["gui_ids"] = ""
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        in_tiltseries: TILTSERIES_TYPE = "",
        fiducial_diameter: Annotated[float, {"label": "Fiducial diameter (nm)"}] = 10.0,
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class AlignTiltSeriesImodPatch(_AlignTiltSeriesJobBase):
    @classmethod
    def command_id(cls):
        return super().command_id() + "-imodpatch"

    @classmethod
    def job_title(cls) -> str:
        return "Align Tilt Series (IMOD Patch Tracking)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_imod_fiducials"] = False
        kwargs["do_aretomo2"] = False
        kwargs["do_imod_patchtrack"] = True
        kwargs["gui_ids"] = ""
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        in_tiltseries: TILTSERIES_TYPE = "",
        patch_size: Annotated[float, {"label": "Patch size (nm)", "min": 1}] = 100,
        patch_overlap: Annotated[
            float, {"label": "Patch overlap (%)", "min": 0, "max": 100}
        ] = 50,
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class AlignTiltSeriesAreTomo2(_AlignTiltSeriesJobBase):
    @classmethod
    def command_id(cls):
        return super().command_id() + "-aretomo2"

    @classmethod
    def job_title(cls) -> str:
        return "Align Tilt Series (AreTomo2)"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_imod_fiducials"] = False
        kwargs["do_aretomo2"] = True
        kwargs["do_imod_patchtrack"] = False
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        in_tiltseries: TILTSERIES_TYPE = "",
        do_aretomo_tiltcorrect: Annotated[
            bool, {"label": "Correct tilt angle offset"}
        ] = False,
        aretomo_tiltcorrect_angle: Annotated[int, {"label": "Tilt angle offset"}] = 999,
        do_aretomo_ctf: Annotated[bool, {"label": "Estimate CTF"}] = False,
        do_aretomo_phaseshift: Annotated[
            bool, {"label": "Estimate phase shift"}
        ] = False,
        other_aretomo_args: Annotated[str, {"label": "Other AreTomo2 arguments"}] = "",
        gpu_ids: GPU_IDS_TYPE = "",
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ReconstructTomogramJob(_RelionBuiltinJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.reconstructtomograms"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        # kwargs["tomo_name"] = " ".join(kwargs["tomo_name"]) ???
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        # Tab 1: I/O
        in_tiltseries: TILTSERIES_TYPE = "",
        generate_split_tomograms: Annotated[
            bool, {"label": "Split tomograms", "group": "I/O"}
        ] = False,
        do_proj: Annotated[
            bool, {"label": "Write 2D projection", "group": "I/O"}
        ] = False,
        centre_proj: Annotated[
            int, {"label": "Central Z-slice (binned pix)", "group": "I/O"}
        ] = 0,
        thickness_proj: Annotated[
            int, {"label": "Number of Z-slices (binned pix)", "group": "I/O"}
        ] = 10,
        # Tab 2: Reconstruct
        xdim: Annotated[
            int, {"label": "Tomogram X size (unbinned pix)", "group": "Reconstruct"}
        ] = 4000,
        ydim: Annotated[
            int, {"label": "Tomogram Y size (unbinned pix)", "group": "Reconstruct"}
        ] = 4000,
        zdim: Annotated[
            int, {"label": "Tomogram Z size (unbinned pix)", "group": "Reconstruct"}
        ] = 2000,
        binned_angpix: Annotated[
            float, {"label": "Pixel size (A)", "group": "Reconstruct"}
        ] = 10.0,
        tiltangle_offset: Annotated[
            float, {"label": "Tilt angle offset (deg)", "group": "Reconstruct"}
        ] = 0.0,
        tomo_name: Annotated[
            str, {"label": "Reconstruct only this tomogram", "group": "Reconstruct"}
        ] = "",
        do_fourier: Annotated[
            bool,
            {"label": "Fourier-inversion with odd/even frames", "group": "Reconstruct"},
        ] = True,
        ctf_intact_first_peak: Annotated[
            bool, {"label": "Ignore CTFs until first peaks", "group": "Reconstruct"}
        ] = True,
        # Tab 3: Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


# TODO: class PickJob(_RelionBuiltinJob):


class ExtractParticlesTomoJob(_RelionBuiltinJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.pseudosubtomo"

    def run(
        self,
        in_optimisation: Annotated[
            str, {"label": "3D Refinement", "group": "I/O"}
        ] = "",
        use_direct_entries: Annotated[
            bool, {"label": "Use direct entries", "group": "I/O"}
        ] = False,
        in_particles: Annotated[str, {"label": "Particles", "group": "I/O"}] = "",
        in_tomograms: Annotated[str, {"label": "Tomograms", "group": "I/O"}] = "",
        in_trajectories: Annotated[str, {"label": "Trajectories", "group": "I/O"}] = "",
        # Reconstruct
        binning: Annotated[
            int, {"label": "Binning factor", "min": 1, "group": "Reconstruct"}
        ] = 1,
        box_size: Annotated[
            int, {"label": "Box size (binned pix)", "group": "Reconstruct"}
        ] = 128,
        crop_size: Annotated[
            int, {"label": "Crop size (binned pix)", "group": "Reconstruct"}
        ] = -1,
        max_dose: Annotated[
            float, {"label": "Maximum dose (e/A^2)", "group": "Reconstruct"}
        ] = -1,
        min_frames: Annotated[
            int, {"label": "Minimum number of frames", "min": 1, "group": "Reconstruct"}
        ] = 1,
        do_stack2d: Annotated[
            bool, {"label": "Extract as 2D stacks", "group": "Reconstruct"}
        ] = True,
        do_float16: Annotated[
            bool, {"label": "Write output in float16", "group": "Reconstruct"}
        ] = True,
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class _DenoiseJobBase(_RelionBuiltinJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.denoisetomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["cryocare_path"] = _configs.get_cryocare_dir()
        return super().normalize_kwargs(**kwargs)


class DenoiseTrain(_DenoiseJobBase):
    @classmethod
    def command_id(cls):
        return super().command_id() + "-train"

    @classmethod
    def job_title(cls) -> str:
        return "CryoCARE Train"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_cryocare_predict"] = False
        kwargs["do_cryocare_train"] = True
        kwargs["care_denoising_model"] = ""
        kwargs["ntiles_x"] = 2
        kwargs["ntiles_y"] = 2
        kwargs["ntiles_z"] = 2
        kwargs["denoising_tomo_name"] = ""
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        in_tomoset: Annotated[str, {"label": "Tomogram sets", "group": "I/O"}] = "",
        tomograms_for_training: Annotated[
            str, {"label": "Tomograms for training", "group": "Train"}
        ] = "",
        number_training_subvolumes: Annotated[
            int, {"label": "Number of sub-volumes per tomogram", "group": "Train"}
        ] = 1200,
        subvolume_dimensions: Annotated[
            int, {"label": "Sub-volume dimensions (pix)", "group": "Train"}
        ] = 72,
        gpu_ids: GPU_IDS_TYPE = "0",
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class DenoisePredict(_DenoiseJobBase):
    @classmethod
    def command_id(cls):
        return super().command_id() + "-predict"

    @classmethod
    def job_title(cls) -> str:
        return "CryoCARE Predict"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs["do_cryocare_predict"] = True
        kwargs["do_cryocare_train"] = False
        kwargs["tomograms_for_training"] = ""
        kwargs["number_training_subvolumes"] = 1200
        kwargs["subvolume_dimensions"] = 72
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        in_tomoset: Annotated[str, {"label": "Tomogram sets", "group": "I/O"}] = "",
        care_denoising_model: Annotated[
            str, {"label": "Denoising model", "group": "I/O"}
        ] = "",
        ntiles_x: Annotated[
            int, {"label": "Number of tiles X", "group": "Predict"}
        ] = 2,
        ntiles_y: Annotated[
            int, {"label": "Number of tiles Y", "group": "Predict"}
        ] = 2,
        ntiles_z: Annotated[
            int, {"label": "Number of tiles Z", "group": "Predict"}
        ] = 2,
        denoising_tomo_name: Annotated[
            str, {"label": "Reconstruct only this tomogram"}
        ] = "",
        gpu_ids: GPU_IDS_TYPE = "0",
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class InitialModel3DJob(_RelionBuiltinJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.initialmodel.tomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["scratch_dir"] = _configs.get_scratch_dir()
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        in_optimisation: Annotated[
            str, {"label": "3D Refinement", "group": "I/O"}
        ] = "",
        use_direct_entries: Annotated[
            bool, {"label": "Use direct entries", "group": "I/O"}
        ] = False,
        in_particles: Annotated[str, {"label": "Particles", "group": "I/O"}] = "",
        in_tomograms: Annotated[str, {"label": "Tomograms", "group": "I/O"}] = "",
        in_trajectories: Annotated[str, {"label": "Trajectories", "group": "I/O"}] = "",
        fn_cont: Annotated[str, {"label": "Continue from here", "group": "I/O"}] = "",
        # CTF
        do_ctf_correction: Annotated[
            bool, {"label": "Do CTF correction", "group": "CTF"}
        ] = True,
        ctf_intact_first_peak: Annotated[
            bool, {"label": "Ignore CTFs until first peak", "group": "CTF"}
        ] = False,
        # Optimisation
        nr_iter: Annotated[
            int, {"label": "Number of iterations", "min": 1, "group": "Optimisation"}
        ] = 200,
        tau_fudge: Annotated[
            float, {"label": "Regularisation parameter T", "group": "Optimisation"}
        ] = 4,
        nr_classes: Annotated[
            int, {"label": "Number of classes", "min": 1, "group": "Optimisation"}
        ] = 1,
        particle_diameter: Annotated[
            float, {"label": "Mask diameter (A)", "group": "Optimisation"}
        ] = 200,
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
        sigma_tilt: Annotated[
            float, {"label": "Prior width on tilt angle", "group": "Optimisation"}
        ] = -1,
        # Compute
        use_parallel_disc_io: Annotated[
            bool, {"label": "Use parallel disc I/O", "group": "Running"}
        ] = True,
        nr_pool: Annotated[
            int, {"label": "Number of pooled particles", "min": 1, "group": "Running"}
        ] = 3,
        do_preread_images: Annotated[
            bool, {"label": "Pre-read particles into RAM", "group": "Running"}
        ] = False,
        do_combine_thru_disc: Annotated[
            bool, {"label": "Combine through disc", "group": "Running"}
        ] = False,
        # Running
        use_gpu: Annotated[
            bool, {"label": "Use GPU acceleration", "group": "Running"}
        ] = True,
        gpu_ids: GPU_IDS_TYPE = "",
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ReconstructParticlesJob(_RelionBuiltinJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.reconstructparticletomo"

    def run(
        self,
        in_optimisation: Annotated[
            str, {"label": "3D Refinement", "group": "I/O"}
        ] = "",
        use_direct_entries: Annotated[
            bool, {"label": "Use direct entries", "group": "I/O"}
        ] = False,
        in_particles: Annotated[str, {"label": "Particles", "group": "I/O"}] = "",
        in_tomograms: Annotated[str, {"label": "Tomograms", "group": "I/O"}] = "",
        in_trajectories: Annotated[str, {"label": "Trajectories", "group": "I/O"}] = "",
        # Average
        binning: Annotated[
            int, {"label": "Binning factor", "min": 1, "group": "Average"}
        ] = 1,
        box_size: Annotated[
            int, {"label": "Box size (binned pix)", "group": "Average"}
        ] = 128,
        crop_size: Annotated[
            int, {"label": "Crop size (binned pix)", "group": "Average"}
        ] = -1,
        snr: Annotated[float, {"label": "SNR", "group": "Average"}] = 0,
        sym_name: Annotated[str, {"label": "Symmetry", "group": "Average"}] = "C1",
        # Helix
        do_helix: Annotated[
            bool, {"label": "Apply helical symmetry", "group": "Helix"}
        ] = False,
        helical_nr_asu: Annotated[
            int,
            {
                "label": "Number of unique asymmetrical units",
                "min": 1,
                "group": "Helix",
            },
        ] = 1,
        helical_twist: Annotated[
            float, {"label": "Helical twist (deg)", "group": "Helix"}
        ] = -1,
        helical_rise: Annotated[
            float, {"label": "Helical rise (A)", "group": "Helix"}
        ] = 4.75,
        helical_tube_outer_diameter: Annotated[
            float, {"label": "Outer helical diameter (A)", "group": "Helix"}
        ] = 200,
        helical_z_percentage: Annotated[
            float,
            {"label": "Central Z length (%)", "min": 0, "max": 100, "group": "Helix"},
        ] = 20,
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


connect_jobs(
    AlignTiltSeriesImodFiducial,
    ReconstructTomogramJob,
    node_mapping={"aligned_tilt_series.star": "in_tiltseries"},
)
connect_jobs(
    ReconstructTomogramJob,
    DenoiseTrain,
    node_mapping={"tomograms.star": "in_tomoset"},
)
connect_jobs(
    DenoiseTrain,
    DenoisePredict,
    node_mapping={"tomograms.star": "in_tomoset"},
)
connect_jobs(
    ExtractParticlesTomoJob,
    InitialModel3DJob,
    node_mapping={"optimisation_set.star": "in_optimisation"},
)
connect_jobs(
    ExtractParticlesTomoJob,
    ReconstructParticlesJob,
    node_mapping={"optimisation_set.star": "in_optimisation"},
)
