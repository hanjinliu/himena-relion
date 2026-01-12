from pathlib import Path

from himena_relion._job_class import _Relion5BuiltinContinue
from himena_relion.relion5._builtins import (
    DynaMightJob,
    MotionCorr2Job,
    MotionCorrOwnJob,
    CtfEstimationJob,
    Class2DJob,
    Class3DNoAlignmentJob,
    InitialModelJob,
    Class3DJob,
    Refine3DJob,
    ManualPickJob,
    AutoPickLogJob,
    AutoPickTemplate2DJob,
    AutoPickTemplate3DJob,
    AutoPickTopazPick,
)
from himena_relion import _annotated as _a


class _MotionCorContinue(_Relion5BuiltinContinue):
    def run(
        self,
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class MotionCorr2Continue(_MotionCorContinue):
    original_class = MotionCorr2Job


class MotionCorrOwnContinue(_MotionCorContinue):
    original_class = MotionCorrOwnJob


class CtfEstimationContinue(_Relion5BuiltinContinue):
    original_class = CtfEstimationJob

    def run(
        self,
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


def _latest_optimiser_star(path: Path) -> str:
    # NOTE: this must be defined before its use in more_node_mappings because
    # the classmethod is called in __init_subclass__
    opt = sorted(path.glob("run_it*_optimiser.star"))
    return str(opt[-1]) if opt else ""


class _AutoPickContinueManually(_Relion5BuiltinContinue):
    @classmethod
    def command_palette_title_prefix(cls) -> str:
        return "Continue Manually -"

    def run(
        self,
        continue_manual: _a.misc.CONTINUE_MANUALLY = True,
        nr_mpi: _a.running.NR_MPI = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class ManualPickContinue(_Relion5BuiltinContinue):
    original_class = ManualPickJob

    def run(
        self,
        fn_in: _a.io.IN_MICROGRAPHS = "",
        do_startend: _a.manualpick.DO_STARTEND = False,
        # Display
        diameter: _a.manualpick.DIAMETER = 100,
        micscale: _a.manualpick.MICSCALE = 0.2,
        sigma_contrast: _a.manualpick.SIGMA_CONTRAST = 3,
        white_val: _a.manualpick.WHITE_VAL = 0,
        black_val: _a.manualpick.BLACK_VAL = 0,
        angpix: _a.manualpick.ANGPIX = -1,
        filter_method: _a.manualpick.FILTER_METHOD = "Band-pass",
        lowpass: _a.manualpick.LOWPASS = 20,
        highpass: _a.manualpick.HIGHPASS = -1,
        # Colors
        do_color: _a.manualpick.DO_COLOR = False,
        color_label: _a.manualpick.COLOR_LABEL = "rlnAutopickFigureOfMerit",
        fn_color: _a.manualpick.FN_COLOR = "",
        blue_value: _a.manualpick.BLUE_VALUE = 0,
        red_value: _a.manualpick.RED_VALUE = 2,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class AutoPickLoGContinueManually(_AutoPickContinueManually):
    original_class = AutoPickLogJob


class AutoPickTemplate2DContinueManually(_AutoPickContinueManually):
    original_class = AutoPickTemplate2DJob


class AutoPickTemplate3DContinueManually(_AutoPickContinueManually):
    original_class = AutoPickTemplate3DJob


class AutoPickTopazContinueManually(_AutoPickContinueManually):
    original_class = AutoPickTopazPick


class Class2DContinue(_Relion5BuiltinContinue):
    original_class = Class2DJob

    def run(
        self,
        # I/O
        fn_cont: _a.io.CONTINUE = "",
        # Optimisation
        tau_fudge: _a.misc.TAU_FUDGE = 2,
        algorithm: _a.class_.OPTIM_ALGORIGHM = {"algorithm": "VDAM", "niter": 200},
        particle_diameter: _a.misc.MASK_DIAMETER = 200,
        do_center: _a.class_.DO_CENTER = True,
        # Sampling
        dont_skip_align: _a.sampling.DONT_SKIP_ALIGN = True,
        psi_sampling: _a.class_.PSI_SAMPLING = 6,
        offset_range_step: _a.sampling.OFFSET_RANGE_STEP = (5, 1),
        allow_coarser: _a.sampling.ALLOW_COARSER_SAMPLING = False,
        # Compute
        do_parallel_discio: _a.compute.USE_PARALLEL_DISC_IO = True,
        nr_pool: _a.compute.NUM_POOL = 3,
        do_preread_images: _a.compute.DO_PREREAD = False,
        use_scratch: _a.compute.USE_SCRATCH = False,
        do_combine_thru_disc: _a.compute.DO_COMBINE_THRU_DISC = False,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def more_node_mappings(cls) -> dict[str, str]:
        return {_latest_optimiser_star: "fn_cont"}


class InitialModelContinue(_Relion5BuiltinContinue):
    original_class = InitialModelJob

    def run(
        self,
        fn_cont: _a.io.CONTINUE = "",
        # Optimisation
        nr_iter: _a.inimodel.NUM_ITER = 200,
        tau_fudge: _a.misc.TAU_FUDGE = 4,
        particle_diameter: _a.misc.MASK_DIAMETER = 200,
        # Compute
        do_parallel_discio: _a.compute.USE_PARALLEL_DISC_IO = True,
        nr_pool: _a.compute.NUM_POOL = 3,
        do_preread_images: _a.compute.DO_PREREAD = False,
        do_combine_thru_disc: _a.compute.DO_COMBINE_THRU_DISC = False,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def more_node_mappings(cls) -> dict[str, str]:
        return {_latest_optimiser_star: "fn_cont"}


class Class3DNoAlignmentContinue(_Relion5BuiltinContinue):
    original_class = Class3DNoAlignmentJob

    def run(
        self,
        fn_cont: _a.io.CONTINUE = "",
        tau_fudge: _a.misc.TAU_FUDGE = 4,
        nr_iter: _a.class_.NUM_ITER = 25,
        particle_diameter: _a.misc.MASK_DIAMETER = 200,
        # Compute
        do_fast_subsets: _a.compute.USE_FAST_SUBSET = False,
        do_parallel_discio: _a.compute.USE_PARALLEL_DISC_IO = True,
        nr_pool: _a.compute.NUM_POOL = 3,
        do_pad1: _a.compute.DO_PAD1 = False,
        do_preread_images: _a.compute.DO_PREREAD = False,
        do_combine_thru_disc: _a.compute.DO_COMBINE_THRU_DISC = False,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def more_node_mappings(cls) -> dict[str, str]:
        return {_latest_optimiser_star: "fn_cont"}


class Class3DContinue(_Relion5BuiltinContinue):
    original_class = Class3DJob

    def run(
        self,
        fn_cont: _a.io.CONTINUE = "",
        tau_fudge: _a.misc.TAU_FUDGE = 4,
        nr_iter: _a.class_.NUM_ITER = 25,
        particle_diameter: _a.misc.MASK_DIAMETER = 200,
        # Sampling
        sampling: _a.sampling.ANG_SAMPLING = "7.5 degrees",
        offset_range_step: _a.sampling.OFFSET_RANGE_STEP = (5, 1),
        do_local_ang_searches: _a.sampling.LOCAL_ANG_SEARCH = False,
        sigma_angles: _a.sampling.SIGMA_ANGLES = 5,
        relax_sym: _a.sampling.RELAX_SYMMETRY = "",
        allow_coarser: _a.sampling.ALLOW_COARSER_SAMPLING = False,
        # Compute
        do_fast_subsets: _a.compute.USE_FAST_SUBSET = False,
        do_parallel_discio: _a.compute.USE_PARALLEL_DISC_IO = True,
        nr_pool: _a.compute.NUM_POOL = 3,
        do_pad1: _a.compute.DO_PAD1 = False,
        do_preread_images: _a.compute.DO_PREREAD = False,
        do_combine_thru_disc: _a.compute.DO_COMBINE_THRU_DISC = False,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Running
        nr_mpi: _a.running.NR_MPI = 1,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def more_node_mappings(cls) -> dict[str, str]:
        return {_latest_optimiser_star: "fn_cont"}


class Refine3DContinue(_Relion5BuiltinContinue):
    original_class = Refine3DJob

    def run(
        self,
        fn_cont: _a.io.CONTINUE = "",
        particle_diameter: _a.misc.MASK_DIAMETER = 200,
        # Compute
        do_parallel_discio: _a.compute.USE_PARALLEL_DISC_IO = True,
        nr_pool: _a.compute.NUM_POOL = 3,
        do_pad1: _a.compute.DO_PAD1 = False,
        do_preread_images: _a.compute.DO_PREREAD = False,
        do_combine_thru_disc: _a.compute.DO_COMBINE_THRU_DISC = False,
        gpu_ids: _a.compute.GPU_IDS = "",
        # Running
        nr_mpi: _a.running.NR_MPI = 3,
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def more_node_mappings(cls) -> dict[str, str]:
        return {_latest_optimiser_star: "fn_cont"}


class _DynaMightContinue(_Relion5BuiltinContinue):
    original_class = DynaMightJob

    @classmethod
    def more_node_mappings(cls) -> dict[str, str]:
        return {_latest_optimiser_star: "fn_cont"}


class DynaMightVisualizeJob(_DynaMightContinue):
    """Visualize the deformations in napari"""

    @classmethod
    def command_id(cls) -> str:
        return "dynamight.visualize.continue"

    @classmethod
    def job_title(cls) -> str:
        return "DynaMight Visualize"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_visualize"] = True
        return kwargs

    def run(
        self,
        # I/O
        fn_checkpoint: _a.dynamight.IN_CHECKPOINT = "",
        gpu_id: _a.dynamight.GPU_ID = 0,
        do_preload: _a.dynamight.DO_PRELOAD = False,
        # Task
        halfset: _a.dynamight.HALFSET = 1,
        # Running
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class DynaMightInverseDeformationJob(_DynaMightContinue):
    """Perform inverse deformation to reconstruct deformed maps"""

    original_class = DynaMightJob

    @classmethod
    def command_id(cls) -> str:
        return "dynamight.inversedeformation.continue"

    @classmethod
    def job_title(cls) -> str:
        return "DynaMight Inverse Deformation"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_inverse"] = True
        return kwargs

    def run(
        self,
        # I/O
        fn_checkpoint: _a.dynamight.IN_CHECKPOINT = "",
        gpu_id: _a.dynamight.GPU_ID = 0,
        do_preload: _a.dynamight.DO_PRELOAD = False,
        # Task
        nr_epochs: _a.dynamight.NR_EPOCHS = 200,
        do_store_deform: _a.dynamight.DO_STORE_DEFORM = False,
        # Running
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")


class DynaMightReconstructJob(_DynaMightContinue):
    """Perform backprojection of the deformations"""

    original_class = DynaMightJob

    @classmethod
    def command_id(cls) -> str:
        return "dynamight.reconstruct.continue"

    @classmethod
    def job_title(cls) -> str:
        return "DynaMight Reconstruct"

    @classmethod
    def normalize_kwargs(cls, **kwargs):
        kwargs = super().normalize_kwargs(**kwargs)
        kwargs["do_reconstruct"] = True
        return kwargs

    def run(
        self,
        # I/O
        fn_checkpoint: _a.dynamight.IN_CHECKPOINT = "",
        gpu_id: _a.dynamight.GPU_ID = 0,
        do_preload: _a.dynamight.DO_PRELOAD = False,
        # Task
        backproject_batchsize: _a.dynamight.BACKPROJECT_BATCHSIZE = 10,
        # Running
        nr_threads: _a.running.NR_THREADS = 1,
        do_queue: _a.running.DO_QUEUE = False,
        min_dedicated: _a.running.MIN_DEDICATED = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")
