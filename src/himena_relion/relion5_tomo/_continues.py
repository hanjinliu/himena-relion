from pathlib import Path

from himena_relion._job_class import _Relion5BuiltinContinue
from himena_relion.relion5_tomo._builtins import (
    InitialModelTomoJob,
    MotionCorr2TomoJob,
    MotionCorrOwnTomoJob,
    CtfEstimationTomoJob,
    Class3DTomoJob,
    Refine3DTomoJob,
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
    original_class = MotionCorr2TomoJob


class MotionCorrOwnContinue(_MotionCorContinue):
    original_class = MotionCorrOwnTomoJob


class CtfEstimationContinue(_Relion5BuiltinContinue):
    original_class = CtfEstimationTomoJob

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


class InitialModelTomoContinue(_Relion5BuiltinContinue):
    original_class = InitialModelTomoJob

    def run(
        self,
        fn_cont: _a.io.CONTINUE = "",
        # Optimisation
        nr_iter: _a.inimodel.NUM_ITER = 200,
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


class Class3DTomoContinue(_Relion5BuiltinContinue):
    original_class = Class3DTomoJob

    def run(
        self,
        fn_cont: _a.io.CONTINUE = "",
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


class Refine3DTomoContinue(_Relion5BuiltinContinue):
    original_class = Refine3DTomoJob

    def run(
        self,
        fn_cont: _a.io.CONTINUE = "",
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
