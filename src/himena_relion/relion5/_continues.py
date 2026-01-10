from pathlib import Path

from himena_relion._job_class import _Relion5BuiltinContinue
from himena_relion.relion5._builtins import (
    MotionCorr2Job,
    MotionCorrOwnJob,
    CtfEstimationJob,
    Class2DJob,
    Class3DNoAlignmentJob,
    InitialModelJob,
    Class3DJob,
    Refine3DJob,
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
