from typing import Annotated, Any

from himena_relion._job_class import connect_jobs
from himena_relion import _configs
from himena_relion.relion5._builtins import (
    CONTINUE_TYPE,
    IN_OPT_TYPE,
    IN_TRAJ_TYPE,
    IN_PARTS_TYPE,
    IN_TOMO_TYPE,
    MASK_TYPE,
    REF_TYPE,
    USE_DIRECT_TYPE,
    USE_GPU_TYPE,
    MPI_TYPE,
    DO_QUEUE_TYPE,
    MIN_DEDICATED_TYPE,
    THREAD_TYPE,
    GPU_IDS_TYPE,
    _RelionBuiltinJob,
)

IN_TILT_TYPE = Annotated[str, {"label": "Tilt series", "group": "I/O"}]


# TODO: class ExcludeTiltJob(_RelionBuiltinJob):


class _AlignTiltSeriesJobBase(_RelionBuiltinJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.aligntiltseries"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["fn_aretomo_exe"] = _configs.get_aretomo2_exe()
        kwargs["fn_batchtomo_exe"] = _configs.get_batchruntomo_exe()
        return super().normalize_kwargs(**kwargs)


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
        kwargs["gui_ids"] = ""
        return super().normalize_kwargs(**kwargs)

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
        in_optimisation: IN_OPT_TYPE = "",
        use_direct_entries: USE_DIRECT_TYPE = False,
        in_particles: IN_PARTS_TYPE = "",
        in_tomograms: IN_TOMO_TYPE = "",
        in_trajectories: IN_TRAJ_TYPE = "",
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
        in_optimisation: IN_OPT_TYPE = "",
        use_direct_entries: USE_DIRECT_TYPE = False,
        in_particles: IN_PARTS_TYPE = "",
        in_tomograms: IN_TOMO_TYPE = "",
        in_trajectories: IN_TRAJ_TYPE = "",
        fn_cont: CONTINUE_TYPE = "",
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
        use_gpu: USE_GPU_TYPE = True,
        gpu_ids: GPU_IDS_TYPE = "",
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class Class3DJob(_RelionBuiltinJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.class3d"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["scratch_dir"] = _configs.get_scratch_dir()
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        in_optimisation: IN_OPT_TYPE = "",
        use_direct_entries: USE_DIRECT_TYPE = False,
        in_particles: IN_PARTS_TYPE = "",
        in_tomograms: IN_TOMO_TYPE = "",
        in_trajectories: IN_TRAJ_TYPE = "",
        fn_ref: REF_TYPE = "",
        fn_mask: MASK_TYPE = "",
        fn_cont: CONTINUE_TYPE = "",
        # Reference
        ref_correct_greyscale: Annotated[
            bool, {"label": "Correct reference greyscale", "group": "Reference"}
        ] = False,
        trust_ref_size: Annotated[
            bool, {"label": "Trust reference size", "group": "Reference"}
        ] = True,
        ini_high: Annotated[
            float, {"label": "Initial low-pass filter (A)", "group": "Reference"}
        ] = 60,
        sym_name: Annotated[str, {"label": "Symmetry", "group": "Reference"}] = "C1",
        # CTF
        do_ctf_correction: Annotated[
            bool, {"label": "Do CTF correction", "group": "CTF"}
        ] = True,
        ctf_intact_first_peak: Annotated[
            bool, {"label": "Ignore CTFs until first peak", "group": "CTF"}
        ] = False,
        # Optimisation
        nr_classes: Annotated[
            int, {"label": "Number of classes", "min": 1, "group": "Optimisation"}
        ] = 1,
        nr_iter: Annotated[
            int, {"label": "Number of iterations", "min": 1, "group": "Optimisation"}
        ] = 25,
        tau_fudge: Annotated[
            float, {"label": "Regularisation parameter T", "group": "Optimisation"}
        ] = 1,
        particle_diameter: Annotated[
            float, {"label": "Mask diameter (A)", "group": "Optimisation"}
        ] = 200,
        do_zero_mask: Annotated[
            bool, {"label": "Mask particles with zeros", "group": "Optimisation"}
        ] = True,
        highres_limit: Annotated[
            float, {"label": "High-resolution limit (A)", "group": "Optimisation"}
        ] = -1,
        # Sampling
        dont_skip_align: Annotated[
            bool, {"label": "Perform image alignment", "group": "Sampling"}
        ] = True,
        sampling: Annotated[
            str, {"label": "Angular sampling interval", "group": "Sampling"}
        ] = "7.5 degrees",
        offset_range: Annotated[
            float, {"label": "Offset search range (pix)", "group": "Sampling"}
        ] = 5,
        offset_step: Annotated[
            float, {"label": "Offset search step (pix)", "group": "Sampling"}
        ] = 1,
        allow_coarser: Annotated[
            bool, {"label": "Allow coarser sampling", "group": "Sampling"}
        ] = False,
        do_local_ang_searches: Annotated[
            bool, {"label": "Perform local angular searches", "group": "Sampling"}
        ] = False,
        sigma_angles: Annotated[
            float, {"label": "Local angular search range", "group": "Sampling"}
        ] = 5,
        relax_sym: Annotated[
            str, {"label": "Relax symmetry", "group": "Sampling"}
        ] = "",
        sigma_tilt: Annotated[
            float, {"label": "Prior width on tilt angle", "group": "Sampling"}
        ] = -1,
        keep_tilt_prior_fixed: Annotated[
            bool, {"label": "Keep tilt-prior fixed", "group": "Sampling"}
        ] = True,
        # Helix
        do_helix: Annotated[
            bool, {"label": "Do helical reconstruction", "group": "Helix"}
        ] = False,
        do_apply_helical_symmetry: Annotated[
            bool, {"label": "Apply helical symmetry", "group": "Helix"}
        ] = True,
        helical_nr_asu: Annotated[
            int, {"label": "Number of asymmetrical units", "group": "Helix"}
        ] = 1,
        helical_twist_initial: Annotated[
            float, {"label": "Initial helical twist (deg)", "group": "Helix"}
        ] = 0,
        helical_rise_initial: Annotated[
            float, {"label": "Initial helical rise (A)", "group": "Helix"}
        ] = 0,
        helical_z_percentage: Annotated[
            float, {"label": "Central Z length (%)", "group": "Helix"}
        ] = 30,
        helical_tube_inner_diameter: Annotated[
            float, {"label": "Inner tube diameter (A)", "group": "Helix"}
        ] = -1,
        helical_tube_outer_diameter: Annotated[
            float, {"label": "Outer tube diameter (A)", "group": "Helix"}
        ] = -1,
        range_rot: Annotated[
            float, {"label": "Range for rot angle (deg)", "group": "Helix"}
        ] = -1,
        range_tilt: Annotated[
            float, {"label": "Range for tilt angle (deg)", "group": "Helix"}
        ] = 15,
        range_psi: Annotated[
            float, {"label": "Range for psi angle (deg)", "group": "Helix"}
        ] = 10,
        do_local_search_helical_symmetry: Annotated[
            bool, {"label": "Do local searches of symmetry", "group": "Helix"}
        ] = False,
        helical_twist_min: Annotated[
            float, {"label": "Helical twist min (deg)", "group": "Helix"}
        ] = 0,
        helical_twist_max: Annotated[
            float, {"label": "Helical twist max (deg)", "group": "Helix"}
        ] = 0,
        helical_twist_inistep: Annotated[
            float, {"label": "Helical twist initial step (deg)", "group": "Helix"}
        ] = 0,
        helical_rise_min: Annotated[
            float, {"label": "Helical rise min (A)", "group": "Helix"}
        ] = 0,
        helical_rise_max: Annotated[
            float, {"label": "Helical rise max (A)", "group": "Helix"}
        ] = 0,
        helical_rise_inistep: Annotated[
            float, {"label": "Helical rise initial step (A)", "group": "Helix"}
        ] = 0,
        helical_range_distance: Annotated[
            float, {"label": "Range factor of local averaging", "group": "Helix"}
        ] = -1,
        # Compute
        do_blush: Annotated[
            bool, {"label": "Use B-factor sharpening", "group": "Compute"}
        ] = False,
        do_fast_subsets: Annotated[
            bool, {"label": "Use fast subsets", "group": "Compute"}
        ] = False,
        do_parallel_discio: Annotated[
            bool, {"label": "Use parallel disc I/O", "group": "Compute"}
        ] = True,
        nr_pool: Annotated[
            int, {"label": "Number of pooled particles", "group": "Compute"}
        ] = 3,
        do_pad1: Annotated[bool, {"label": "Skip padding", "group": "Compute"}] = False,
        do_preread_images: Annotated[
            bool, {"label": "Pre-read all particles into RAM", "group": "Compute"}
        ] = False,
        do_combine_thru_disc: Annotated[
            bool, {"label": "Combine iterations through disc", "group": "Compute"}
        ] = False,
        use_gpu: USE_GPU_TYPE = False,
        gpu_ids: GPU_IDS_TYPE = "",
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class Refine3DJob(_RelionBuiltinJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.refine3d.tomo"

    @classmethod
    def normalize_kwargs(cls, **kwargs) -> dict[str, Any]:
        kwargs["scratch_dir"] = _configs.get_scratch_dir()
        return super().normalize_kwargs(**kwargs)

    def run(
        self,
        in_optimisation: IN_OPT_TYPE = "",
        use_direct_entries: USE_DIRECT_TYPE = False,
        in_particles: IN_PARTS_TYPE = "",
        in_tomograms: IN_TOMO_TYPE = "",
        in_trajectories: IN_TRAJ_TYPE = "",
        fn_ref: REF_TYPE = "",
        fn_mask: MASK_TYPE = "",
        fn_cont: CONTINUE_TYPE = "",
        # Reference
        ref_correct_greyscale: Annotated[
            bool, {"label": "Correct reference greyscale", "group": "Compute"}
        ] = False,
        trust_ref_size: Annotated[
            bool, {"label": "Trust reference size", "group": "Compute"}
        ] = True,
        ini_high: Annotated[
            float, {"label": "Initial low-pass filter (A)", "group": "Reference"}
        ] = 60,
        sym_name: Annotated[str, {"label": "Symmetry", "group": "Reference"}] = "C1",
        # CTF
        do_ctf_correction: Annotated[
            bool, {"label": "Do CTF correction", "group": "CTF"}
        ] = True,
        ctf_intact_first_peak: Annotated[
            bool, {"label": "Ignore CTFs until first peak", "group": "CTF"}
        ] = False,
        # Optimisation
        particle_diameter: Annotated[
            float, {"label": "Mask diameter (A)", "group": "Optimisation"}
        ] = 200,
        do_zero_mask: Annotated[
            bool, {"label": "Mask particles with zeros", "group": "Optimisation"}
        ] = True,
        do_solvent_fsc: Annotated[
            bool, {"label": "Use solvent-corrected FSCs", "group": "Compute"}
        ] = False,
        do_blush: Annotated[
            bool, {"label": "Use B-factor sharpening", "group": "Compute"}
        ] = False,
        # Auto-sampling
        sampling: Annotated[
            str, {"label": "Angular sampling interval", "group": "Auto-sampling"}
        ] = "7.5 degrees",
        offset_range: Annotated[
            float, {"label": "Offset search range (pix)", "group": "Auto-sampling"}
        ] = 5,
        offset_step: Annotated[
            float, {"label": "Offset search step (pix)", "group": "Auto-sampling"}
        ] = 1,
        auto_local_sampling: Annotated[
            str, {"label": "Local angular sampling", "group": "Auto-sampling"}
        ] = "1.8 degrees",
        relax_sym: Annotated[
            str, {"label": "Relax symmetry", "group": "Auto-sampling"}
        ] = "",
        sigma_tilt: Annotated[
            float, {"label": "Prior width on tilt angle", "group": "Auto-sampling"}
        ] = -1,
        keep_tilt_prior_fixed: Annotated[
            bool, {"label": "Keep tilt-prior fixed", "group": "Auto-sampling"}
        ] = True,
        # Helix
        do_helix: Annotated[
            bool, {"label": "Do helical reconstruction", "group": "Helix"}
        ] = False,
        do_apply_helical_symmetry: Annotated[
            bool, {"label": "Apply helical symmetry", "group": "Helix"}
        ] = True,
        helical_nr_asu: Annotated[
            int, {"label": "Number of asymmetrical units", "group": "Helix"}
        ] = 1,
        helical_twist_initial: Annotated[
            float, {"label": "Initial helical twist (deg)", "group": "Helix"}
        ] = 0,
        helical_rise_initial: Annotated[
            float, {"label": "Initial helical rise (A)", "group": "Helix"}
        ] = 0,
        helical_z_percentage: Annotated[
            float, {"label": "Central Z length (%)", "group": "Helix"}
        ] = 30,
        helical_tube_inner_diameter: Annotated[
            float, {"label": "Inner tube diameter (A)", "group": "Helix"}
        ] = -1,
        helical_tube_outer_diameter: Annotated[
            float, {"label": "Outer tube diameter (A)", "group": "Helix"}
        ] = -1,
        range_rot: Annotated[
            float, {"label": "Range for rot angle (deg)", "group": "Helix"}
        ] = -1,
        range_tilt: Annotated[
            float, {"label": "Range for tilt angle (deg)", "group": "Helix"}
        ] = 15,
        range_psi: Annotated[
            float, {"label": "Range for psi angle (deg)", "group": "Helix"}
        ] = 10,
        do_local_search_helical_symmetry: Annotated[
            bool, {"label": "Do local searches of symmetry", "group": "Helix"}
        ] = False,
        helical_twist_min: Annotated[
            float, {"label": "Helical twist min (deg)", "group": "Helix"}
        ] = 0,
        helical_twist_max: Annotated[
            float, {"label": "Helical twist max (deg)", "group": "Helix"}
        ] = 0,
        helical_twist_inistep: Annotated[
            float, {"label": "Helical twist initial step (deg)", "group": "Helix"}
        ] = 0,
        helical_rise_min: Annotated[
            float, {"label": "Helical rise min (A)", "group": "Helix"}
        ] = 0,
        helical_rise_max: Annotated[
            float, {"label": "Helical rise max (A)", "group": "Helix"}
        ] = 0,
        helical_rise_inistep: Annotated[
            float, {"label": "Helical rise initial step (A)", "group": "Helix"}
        ] = 0,
        helical_range_distance: Annotated[
            float, {"label": "Range factor of local averaging", "group": "Helix"}
        ] = -1,
        # Compute
        do_parallel_discio: Annotated[
            bool, {"label": "Use parallel disc I/O", "group": "Compute"}
        ] = True,
        nr_pool: Annotated[
            int, {"label": "Number of pooled particles", "group": "Compute"}
        ] = 3,
        do_pad1: Annotated[bool, {"label": "Skip padding", "group": "Compute"}] = False,
        do_preread_images: Annotated[
            bool, {"label": "Pre-read all particles into RAM", "group": "Compute"}
        ] = False,
        do_combine_thru_disc: Annotated[
            bool, {"label": "Combine iterations through disc", "group": "Compute"}
        ] = False,
        use_gpu: USE_GPU_TYPE = False,
        gpu_ids: GPU_IDS_TYPE = "",
        # Running
        nr_mpi: MPI_TYPE = 1,
        nr_threads: THREAD_TYPE = 1,
        do_queue: DO_QUEUE_TYPE = False,
        min_dedicated: MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ReconstructParticlesJob(_RelionBuiltinJob):
    @classmethod
    def type_label(cls) -> str:
        return "relion.reconstructparticletomo"

    def run(
        self,
        in_optimisation: IN_OPT_TYPE = "",
        use_direct_entries: USE_DIRECT_TYPE = False,
        in_particles: IN_PARTS_TYPE = "",
        in_tomograms: IN_TOMO_TYPE = "",
        in_trajectories: IN_TRAJ_TYPE = "",
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
