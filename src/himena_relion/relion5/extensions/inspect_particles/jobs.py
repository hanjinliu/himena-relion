from himena_relion.consts import MenuId
from himena_relion.external import RelionExternalJob
from himena_relion._annotated.io import IN_PARTICLES, IN_MICROGRAPHS
from himena_relion.relion5.extensions.inspect_particles.widgets import (
    InspectParticlesSPAWidget,
)


class InspectParticlesSPA(RelionExternalJob):
    """Inspect picked/refined particles in 2D micrographs."""

    def output_nodes(self):
        return [
            ("micrographs.star", "MicrographGroupMetadata.star"),
            ("particles.star", "ParticleGroupMetadata.star"),
        ]

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5:{cls.__name__}"

    @classmethod
    def job_title(cls):
        return "Inspect Particles (SPA)"

    @classmethod
    def menu_id(cls):
        return MenuId.RELION_PICK_JOB

    def run(
        self,
        in_mics: IN_MICROGRAPHS = "",  # path
        in_parts: IN_PARTICLES = "",  # path
    ):
        out_job_dir = self.output_job_dir
        out_mics = out_job_dir.path / "micrographs.star"
        out_parts = out_job_dir.path / "particles.star"
        out_mics.write_bytes(out_job_dir.resolve_path(in_mics).read_bytes())
        out_parts.write_bytes(out_job_dir.resolve_path(in_parts).read_bytes())

    def provide_widget(self, job_dir):
        return InspectParticlesSPAWidget(job_dir)
