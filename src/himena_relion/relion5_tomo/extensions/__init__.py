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
    from himena_relion.relion5.extensions import ShiftMapJob
    from himena_relion.relion5_tomo._builtins import (
        ReconstructParticlesJob,
        ExtractParticlesTomoJob,
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


_connect_jobs()
del _connect_jobs
