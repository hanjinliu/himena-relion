from pathlib import Path

from himena_relion._job_class import _RelionBuiltinContinue
from himena_relion.relion5_tomo._builtins import (
    InitialModelTomoJob,
    Class3DTomoJob,
    Refine3DTomoJob,
)
from himena_relion import _annotated as _a


def _latest_optimiser_star(path: Path) -> str:
    # NOTE: this must be defined before its use in more_node_mappings because
    # the classmethod is called in __init_subclass__
    opt = sorted(path.glob("run_it*_optimiser.star"))
    return str(opt[-1]) if opt else ""


class InitialModelTomoContinue(_RelionBuiltinContinue):
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
        nr_mpi: _a.running.MPI_TYPE = 1,
        nr_threads: _a.running.THREAD_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def more_node_mappings(cls) -> dict[str, str]:
        return {_latest_optimiser_star: "fn_cont"}


class Class3DTomoContinue(_RelionBuiltinContinue):
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
        nr_mpi: _a.running.MPI_TYPE = 1,
        nr_threads: _a.running.THREAD_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def more_node_mappings(cls) -> dict[str, str]:
        return {_latest_optimiser_star: "fn_cont"}


class Refine3DTomoContinue(_RelionBuiltinContinue):
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
        nr_mpi: _a.running.MPI_TYPE = 3,
        nr_threads: _a.running.THREAD_TYPE = 1,
        do_queue: _a.running.DO_QUEUE_TYPE = False,
        min_dedicated: _a.running.MIN_DEDICATED_TYPE = 1,
    ):
        raise NotImplementedError("This is a builtin job placeholder.")

    @classmethod
    def more_node_mappings(cls) -> dict[str, str]:
        return {_latest_optimiser_star: "fn_cont"}
