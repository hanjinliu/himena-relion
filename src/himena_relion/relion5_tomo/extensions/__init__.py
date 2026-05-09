"""Built-in extensions for Relion 5 Tomo."""

from himena_relion.relion5_tomo.extensions.erase_gold import FindBeads3D, EraseGold
from himena_relion.relion5_tomo.extensions.exclude_tilts import AutoExcludeTiltImages
from himena_relion.relion5_tomo.extensions.hybridize import TakeZeroTiltMicrographs
from himena_relion.relion5_tomo.extensions.inspect_particles import InspectParticles

__all__ = [
    "FindBeads3D",
    "AutoExcludeTiltImages",
    "TakeZeroTiltMicrographs",
    "EraseGold",
    "InspectParticles",
]


def _connect_jobs():
    from himena_relion._job_class import connect_jobs
    from himena_relion.relion5.extensions import ShiftMapJob, ManualMaskCreation
    from himena_relion.relion5_tomo._connections import mask_create_search_halfmap
    from himena_relion.relion5_tomo._builtins import (
        ReconstructParticlesJob,
        ExtractParticlesTomoJob,
        InitialModelTomoJob,
        Refine3DTomoJob,
        PostProcessTomoJob,
    )

    connect_jobs(
        ShiftMapJob,
        ReconstructParticlesJob,
        node_mapping={
            ShiftMapJob.OUTPUT_PARTICLES: "in_optim.in_particles",
        },
    )
    connect_jobs(
        ShiftMapJob,
        ExtractParticlesTomoJob,
        node_mapping={
            ShiftMapJob.OUTPUT_PARTICLES: "in_optim.in_particles",
        },
    )

    connect_jobs(
        InitialModelTomoJob,
        ManualMaskCreation,
        node_mapping={"initial_model.mrc": "in_3dref"},
    )
    connect_jobs(
        Refine3DTomoJob,
        ManualMaskCreation,
        node_mapping={"run_class001.mrc": "in_3dref"},
    )
    connect_jobs(
        ReconstructParticlesJob,
        ManualMaskCreation,
        node_mapping={"merged.mrc": "in_3dref"},
    )

    connect_jobs(
        ManualMaskCreation,
        PostProcessTomoJob,
        node_mapping={
            mask_create_search_halfmap: "fn_in",
            "mask.mrc": "fn_mask",
        },
    )


_connect_jobs()
del _connect_jobs
