from typing import Annotated, Any

from himena_relion._job_class import connect_jobs, _RelionBuiltinJob, parse_string
from himena_relion import _configs
from himena_relion._widgets._magicgui import OptimisationSetEdit
from himena_relion._widgets._path_input import PathDrop
from himena_relion.relion5._builtins import (
    ANG_SAMPLING_TYPE,
    CONTINUE_TYPE,
    DO_APPLY_HELICAL_SYMMETRY_TYPE,
    DO_BLUSH_TYPE,
    DO_COMBINE_THRU_DISC_TYPE,
    DO_CTF_TYPE,
    DO_HELIX_TYPE,
    DO_LOCAL_SEARCH_HELICAL_SYMMETRY_TYPE,
    DO_PREREAD_TYPE,
    HALFMAP_TYPE,
    HELICAL_NR_ASU_TYPE,
    HELICAL_RANGE_DIST_TYPE,
    HELICAL_RISE_INITIAL_TYPE,
    HELICAL_RISE_RANGE_TYPE,
    HELICAL_TUBE_DIAMETER_RANGE_TYPE,
    HELICAL_TWIST_INITIAL_TYPE,
    HELICAL_TWIST_RANGE_TYPE,
    HELICAL_Z_PERCENTAGE_TYPE,
    IGNORE_CTF_TYPE,
    INITIAL_LOWPASS_TYPE,
    KEEP_TILT_PRIOR_FIXED_TYPE,
    LOC_ANG_SAMPLING_TYPE,
    MASK_DIAMETER_TYPE,
    MASK_TYPE,
    MASK_WITH_ZEROS_TYPE,
    NUM_CLASS_TYPE,
    NUM_ITER_TYPE,
    NUM_POOL_TYPE,
    OFFSET_RANGE_STEP_TYPE,
    PROCESS_TYPE,
    REF_CORRECT_GRAY_TYPE,
    REF_SYMMETRY_TYPE,
    REF_TYPE,
    RELAX_SYMMETRY_TYPE,
    ROT_TILT_PSI_RANGE_TYPE,
    SIGMA_TILT_TYPE,
    T_TYPE,
    TRUST_REF_SIZE_TYPE,
    USE_GPU_TYPE,
    MPI_TYPE,
    DO_QUEUE_TYPE,
    MIN_DEDICATED_TYPE,
    THREAD_TYPE,
    GPU_IDS_TYPE,
    USE_PARALLEL_DISC_IO_TYPE,
    CtfEstimationJob,
    PostProcessingJob,
)

IN_TILT_TYPE = Annotated[
    str,
    {
        "label": "Input tilt series",
        "widget_type": PathDrop,
        "type_label": "TomogramGroupMetadata",
        "group": "I/O",
    },
]
IN_PARTICLES = Annotated[
    str,
    {
        "label": "Input particles (optional)",
        "widget_type": PathDrop,
        "type_label": "ParticleGroupMetadata",
        "group": "I/O",
    },
]
IN_OPTIM = Annotated[
    dict,
    {"label": "Input particles", "group": "I/O", "widget_type": OptimisationSetEdit},
]


def norm_optim(**kwargs):
    optim = kwargs.pop("in_optim", {})
    kwargs["in_optimisation"] = optim.get("in_optimisation", "")
    kwargs["use_direct_entries"] = parse_string(
        optim.get("use_direct_entries", False), bool
    )
    kwargs["in_particles"] = optim.get("in_particles", "")
    kwargs["in_tomograms"] = optim.get("in_tomograms", "")
    kwargs["in_trajectories"] = optim.get("in_trajectories", "")
    return kwargs


def norm_optim_inv(**kwargs):
    if "in_optim" not in kwargs:
        kwargs["in_optim"] = {
            "in_optimisation": kwargs.pop("in_optimisation", ""),
            "use_direct_entries": kwargs.pop("use_direct_entries", False),
            "in_particles": kwargs.pop("in_particles", ""),
            "in_tomograms": kwargs.pop("in_tomograms", ""),
            "in_trajectories": kwargs.pop("in_trajectories", ""),
        }
    return kwargs


class _Relion5TomoJob(_RelionBuiltinJob):
    @classmethod
    def command_palette_title_prefix(cls):
        return "RELION 5 Tomo:"


class ExcludeTiltJob(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.excludetilts"

    def run(
        self,
        in_tiltseries: IN_TILT_TYPE = "",
        cache_size: Annotated[
            int,
            {
                "label": "Number of cached tilt series",
                "min": 1,
                "max": 10,
                "group": "I/O",
            },
        ] = 5,
        nr_mpi: MPI_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class _AlignTiltSeriesJobBase(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.aligntiltseries"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_aretomo_exe"] = _configs.get_aretomo2_exe()
        kwargs["fn_batchtomo_exe"] = _configs.get_batchruntomo_exe()
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("fn_aretomo_exe", None)
        kwargs.pop("fn_batchtomo_exe", None)
        return super().normalize_kwargs_inv(**kwargs)


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
        kwargs["gpu_ids"] = ""
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("do_imod_fiducials", None)
        kwargs.pop("do_aretomo2", None)
        kwargs.pop("do_imod_patchtrack", None)
        kwargs.pop("gpu_ids", None)
        # remove parameters from other methods
        kwargs.pop("patch_size", None)
        kwargs.pop("patch_overlap", None)
        kwargs.pop("do_aretomo_tiltcorrect", None)
        kwargs.pop("aretomo_tiltcorrect_angle", None)
        kwargs.pop("do_aretomo_ctf", None)
        kwargs.pop("do_aretomo_phaseshift", None)
        kwargs.pop("other_aretomo_args", None)
        return kwargs

    def run(
        self,
        in_tiltseries: IN_TILT_TYPE = "",
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
        kwargs["gpu_ids"] = ""
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("do_imod_fiducials", None)
        kwargs.pop("do_aretomo2", None)
        kwargs.pop("do_imod_patchtrack", None)
        kwargs.pop("gpu_ids", None)
        kwargs.pop("fiducial_diameter", None)
        kwargs.pop("do_aretomo_tiltcorrect", None)
        kwargs.pop("aretomo_tiltcorrect_angle", None)
        kwargs.pop("do_aretomo_ctf", None)
        kwargs.pop("do_aretomo_phaseshift", None)
        kwargs.pop("other_aretomo_args", None)
        return kwargs

    def run(
        self,
        in_tiltseries: IN_TILT_TYPE = "",
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

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("fiducial_diameter", None)
        kwargs.pop("patch_size", None)
        kwargs.pop("patch_overlap", None)
        kwargs.pop("do_imod_fiducials", None)
        kwargs.pop("do_aretomo2", None)
        kwargs.pop("do_imod_patchtrack", None)
        return kwargs

    def run(
        self,
        in_tiltseries: IN_TILT_TYPE = "",
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


class ReconstructTomogramJob(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.reconstructtomograms"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        # kwargs["tomo_name"] = " ".join(kwargs["tomo_name"]) ???
        if "dims" in kwargs:
            xdim, ydim, zdim = kwargs.pop("dims")
            kwargs["xdim"] = xdim
            kwargs["ydim"] = ydim
            kwargs["zdim"] = zdim
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs["dims"] = (
            kwargs.pop("xdim", 4000),
            kwargs.pop("ydim", 4000),
            kwargs.pop("zdim", 2000),
        )
        return kwargs

    def run(
        self,
        # Tab 1: I/O
        in_tiltseries: IN_TILT_TYPE = "",
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
        dims: Annotated[
            tuple[int, int, int],
            {"label": "Tomogram X, Y, Z size (unbinned pix)", "group": "Reconstruct"},
        ] = (4000, 4000, 2000),
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
        ctf_intact_first_peak: IGNORE_CTF_TYPE = True,
        # Tab 3: Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class PickJob(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.picktomo"

    def run(
        self,
        in_tomoset: IN_TILT_TYPE = "",
        in_star_file: IN_PARTICLES = "",
        pick_mode: Annotated[
            str,
            {
                "label": "Picking mode",
                "choices": ["particles", "spheres", "surfaces", "filaments"],
                "group": "I/O",
            },
        ] = "particles",
        particle_spacing: Annotated[
            float, {"label": "Particle spacing (A)", "group": "I/O"}
        ] = -1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ExtractParticlesTomoJob(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.pseudosubtomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        return norm_optim(**super().normalize_kwargs(**kwargs))

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        return norm_optim_inv(**super().normalize_kwargs_inv(**kwargs))

    def run(
        self,
        in_optim: IN_OPTIM = None,
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


class _DenoiseJobBase(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.denoisetomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["cryocare_path"] = _configs.get_cryocare_dir()
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs.pop("cryocare_path", None)
        return super().normalize_kwargs_inv(**kwargs)


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

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("do_cryocare_predict", None)
        kwargs.pop("do_cryocare_train", None)
        kwargs.pop("care_denoising_model", None)
        kwargs.pop("ntiles_x", None)
        kwargs.pop("ntiles_y", None)
        kwargs.pop("ntiles_z", None)
        kwargs.pop("denoising_tomo_name", None)
        return kwargs

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
        if "ntiles" in kwargs:
            ntile_x, ntile_y, ntile_z = kwargs.pop("ntiles")
            kwargs["ntiles_x"] = ntile_x
            kwargs["ntiles_y"] = ntile_y
            kwargs["ntiles_z"] = ntile_z
        return super().normalize_kwargs(**kwargs)

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = super().normalize_kwargs_inv(**kwargs)
        kwargs.pop("do_cryocare_predict", None)
        kwargs.pop("do_cryocare_train", None)
        kwargs.pop("tomograms_for_training", None)
        kwargs.pop("number_training_subvolumes", None)
        kwargs.pop("subvolume_dimensions", None)
        kwargs["ntiles"] = (
            kwargs.pop("ntiles_x", 2),
            kwargs.pop("ntiles_y", 2),
            kwargs.pop("ntiles_z", 2),
        )
        return kwargs

    def run(
        self,
        in_tomoset: Annotated[str, {"label": "Tomogram sets", "group": "I/O"}] = "",
        care_denoising_model: Annotated[
            str, {"label": "Denoising model", "group": "I/O"}
        ] = "",
        ntiles: Annotated[
            tuple[int, int, int],
            {"label": "Number of tiles (X, Y, Z)", "group": "Predict"},
        ] = (2, 2, 2),
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


class InitialModel3DJob(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.initialmodel.tomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["scratch_dir"] = _configs.get_scratch_dir()
        return norm_optim(**super().normalize_kwargs(**kwargs))

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        return norm_optim_inv(**super().normalize_kwargs_inv(**kwargs))

    def run(
        self,
        in_optim: IN_OPTIM = None,
        fn_cont: CONTINUE_TYPE = "",
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
        sigma_tilt: SIGMA_TILT_TYPE = -1,
        # Compute
        use_parallel_disc_io: USE_PARALLEL_DISC_IO_TYPE = True,
        nr_pool: NUM_POOL_TYPE = 3,
        do_preread_images: DO_PREREAD_TYPE = False,
        do_combine_thru_disc: DO_COMBINE_THRU_DISC_TYPE = False,
        # Running
        use_gpu: USE_GPU_TYPE = True,
        gpu_ids: GPU_IDS_TYPE = "",
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class Class3DJob(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.class3d"

    @classmethod
    def command_id(cls):
        return super().command_id() + "-tomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["scratch_dir"] = _configs.get_scratch_dir()
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
        return norm_optim(**super().normalize_kwargs(**kwargs))

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
        return norm_optim_inv(**super().normalize_kwargs_inv(**kwargs))

    def run(
        self,
        in_optim: IN_OPTIM = None,
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


class Refine3DTomoJob(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.refine3d.tomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["scratch_dir"] = _configs.get_scratch_dir()
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
        return norm_optim(**super().normalize_kwargs(**kwargs))

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
        return norm_optim_inv(**super().normalize_kwargs_inv(**kwargs))

    def run(
        self,
        in_optim: IN_OPTIM = None,
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
        auto_faster: Annotated[
            bool, {"label": "Use finer angular sampling faster", "group": "Sampling"}
        ] = False,
        sigma_tilt: SIGMA_TILT_TYPE = -1,
        # Helix
        do_helix: DO_HELIX_TYPE = False,
        do_apply_helical_symmetry: DO_APPLY_HELICAL_SYMMETRY_TYPE = True,
        helical_nr_asu: HELICAL_NR_ASU_TYPE = 1,
        keep_tilt_prior_fixed: KEEP_TILT_PRIOR_FIXED_TYPE = True,
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


class ReconstructParticlesJob(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.reconstructparticletomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        return norm_optim(**super().normalize_kwargs(**kwargs))

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        return norm_optim_inv(**super().normalize_kwargs_inv(**kwargs))

    def run(
        self,
        in_optim: IN_OPTIM = None,
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
        do_helix: DO_HELIX_TYPE = False,
        helical_nr_asu: HELICAL_NR_ASU_TYPE = 1,
        helical_twist: Annotated[
            float, {"label": "Helical twist (deg)", "group": "Helix"}
        ] = -1,
        helical_rise: Annotated[
            float, {"label": "Helical rise (A)", "group": "Helix"}
        ] = 4.75,
        helical_tube_outer_diameter: Annotated[
            float, {"label": "Outer helical diameter (A)", "group": "Helix"}
        ] = 200,
        helical_z_percentage: HELICAL_Z_PERCENTAGE_TYPE = 20,
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class CtfRefineTomoJob(_Relion5TomoJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.ctfrefinetomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs = norm_optim(**super().normalize_kwargs(**kwargs))
        if "lambda" not in kwargs:
            kwargs["lambda"] = kwargs.pop("lambda_param", 0.1)
        return kwargs

    @classmethod
    def normalize_kwargs_inv(cls, **kwargs) -> dict[str, Any]:
        kwargs = norm_optim_inv(**super().normalize_kwargs_inv(**kwargs))
        if "lambda" in kwargs:
            kwargs["lambda_param"] = kwargs.pop("lambda")
        return kwargs

    def run(
        self,
        in_optim: IN_OPTIM = None,
        in_halfmaps: HALFMAP_TYPE = "",
        in_refmask: MASK_TYPE = "",
        in_post: PROCESS_TYPE = "",
        # CTF Refinement
        box_size: Annotated[
            int, {"label": "Box size of estimation (pix)", "group": "Defocus"}
        ] = 128,
        do_defocus: Annotated[
            bool, {"label": "Refine defocus", "group": "Defocus"}
        ] = True,
        focus_range: Annotated[
            float, {"label": "Defocus search range (A)", "group": "Defocus"}
        ] = 3000,
        do_reg_def: Annotated[
            bool, {"label": "Do defocus regularisation", "group": "Defocus"}
        ] = False,
        lambda_param: Annotated[
            float, {"label": "Defocus regularisation lambda", "group": "Defocus"}
        ] = 0.1,
        do_scale: Annotated[
            bool, {"label": "Refine contrast scale", "group": "Defocus"}
        ] = True,
        do_frame_scale: Annotated[
            bool, {"label": "Refine scale per frame", "group": "Defocus"}
        ] = True,
        do_tomo_scale: Annotated[
            bool, {"label": "Refine scale per tomogram", "group": "Defocus"}
        ] = False,
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


# class FrameAlignTomoJob(_Relion5TomoJob):

connect_jobs(
    CtfEstimationJob,
    ExcludeTiltJob,
    node_mapping={"tilt_series_ctf.star": "in_tiltseries"},
)
connect_jobs(
    ExcludeTiltJob,
    AlignTiltSeriesImodFiducial,
    node_mapping={"selected_tilt_series.star": "in_tiltseries"},
)
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
    ReconstructTomogramJob,
    PickJob,
    node_mapping={"tomograms.star": "in_tomoset"},
)
connect_jobs(
    DenoisePredict,
    PickJob,
    node_mapping={"tomograms.star": "in_tomoset"},
)
connect_jobs(
    PickJob,
    ExtractParticlesTomoJob,
    node_mapping={"optimisation_set.star": "in_optim.in_optimisation"},
)
connect_jobs(
    ExtractParticlesTomoJob,
    InitialModel3DJob,
    node_mapping={"optimisation_set.star": "in_optim.in_optimisation"},
)
connect_jobs(
    ExtractParticlesTomoJob,
    ReconstructParticlesJob,
    node_mapping={"optimisation_set.star": "in_optim.in_optimisation"},
)
connect_jobs(
    InitialModel3DJob,
    Class3DJob,
    node_mapping={
        "optimisation_set.star": "in_optim.in_optimisation",
        "initial_model.mrc": "fn_ref",
    },
)
connect_jobs(
    InitialModel3DJob,
    Refine3DTomoJob,
    node_mapping={
        "optimisation_set.star": "in_optim.in_optimisation",
        "initial_model.mrc": "fn_ref",
    },
)
connect_jobs(
    Class3DJob,
    Refine3DTomoJob,
)
connect_jobs(
    ReconstructParticlesJob,
    Refine3DTomoJob,
    node_mapping={
        "optimisation_set.star": "in_optim.in_optimisation",
        "merged.mrc": "fn_ref",
    },
)
connect_jobs(
    ReconstructParticlesJob,
    PostProcessingJob,
    node_mapping={"half1.mrc": "fn_in"},
)
connect_jobs(
    PostProcessingJob,
    CtfRefineTomoJob,
    node_mapping={"postprocess.star": "in_post"},
)
