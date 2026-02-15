import subprocess
from typing import Annotated

from himena_relion.consts import MenuId
from himena_relion.external import RelionExternalJob
from himena_relion._annotated.io import IN_PARTICLES
from himena_relion import _annotated as _a


_COMMAND = "relion_particle_symmetry_expand"
_OUTPUT_PARTICLES = "particles_expanded.star"


class SymmetryExpansionJob(RelionExternalJob):
    """Create a new set of particles by symmetry expansion."""

    def output_nodes(self):
        return [(_OUTPUT_PARTICLES, "ParticleGroupMetadata.star")]

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5:{cls.__name__}"

    @classmethod
    def job_title(cls):
        return "Symmetry Expansion"

    @classmethod
    def menu_id(cls):
        return MenuId.RELION_UTILS_JOB

    def run(
        self,
        in_parts: IN_PARTICLES,  # path
        symmetry: Annotated[str, {"label": "Symmetry"}] = "C1",
    ):
        out_job_dir = self.output_job_dir
        args = [
            _COMMAND,
            "--i",
            str(in_parts),
            "--o",
            str(out_job_dir.path / _OUTPUT_PARTICLES),
            "--sym",
            symmetry,
        ]
        subprocess.run(args, check=True)


class HelicalSymmetryExpansionJob(RelionExternalJob):
    """Create a new set of particles by helical symmetry expansion."""

    def output_nodes(self):
        return [(_OUTPUT_PARTICLES, "ParticleGroupMetadata.star")]

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5:{cls.__name__}"

    @classmethod
    def job_title(cls):
        return "Helical Symmetry Expansion"

    @classmethod
    def menu_id(cls):
        return MenuId.RELION_UTILS_JOB

    def run(
        self,
        in_parts: IN_PARTICLES,  # path
        twist: _a.helix.HELICAL_TWIST = 0.0,
        rise: _a.helix.HELICAL_RISE = 0.0,
        angpix: Annotated[float, {"label": "Pixel size (Å)"}] = 1.0,
        num_asu: Annotated[int, {"label": "Number of asymmetric units"}] = 1,
    ):
        out_job_dir = self.output_job_dir
        args = [
            _COMMAND,
            "--i",
            str(in_parts),
            "--o",
            str(out_job_dir.path / _OUTPUT_PARTICLES),
            "--helix",
            "--angpix",
            str(angpix),
            "--twist",
            str(twist),
            "--rise",
            str(rise),
            "--asu",
            str(num_asu),
        ]
        subprocess.run(args, check=True)
