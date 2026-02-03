from pathlib import Path

from starfile_rs import empty_star
from himena_relion._job_class import connect_jobs
from himena_relion.external import RelionExternalJob
from himena_relion.relion5._builtins import (
    SelectSplitJob,
    SelectRemoveDuplicatesJob,
    SelectClassesInteractiveJob,
)
from himena_relion.relion5_tomo._builtins import (
    Refine3DTomoJob,
    ExtractParticlesTomoJob,
    InitialModelTomoJob,
    ReconstructParticlesJob,
    Class3DTomoJob,
)
from himena_relion._annotated.io import IN_TILT, IN_PARTICLES
from himena_relion.schemas import OptimisationSetModel
from .widgets import QInspectViewer


class InspectParticles(RelionExternalJob):
    """View particles in tomograms.

    This job is also useful to create an optimisation_set.star from tomograms.star and
    particles.star files. Unlike Pick job, this job does not discard any particle
    properties in the input particles.star file.
    """

    def output_nodes(self):
        return [("optimisation_set.star", "TomoOptimisationSet.star")]

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5_tomo:{cls.__name__}"

    @classmethod
    def job_title(cls):
        return "Inspect Particles"

    def provide_widget(self, job_dir) -> QInspectViewer:
        return QInspectViewer(job_dir)

    def run(
        self,
        in_mics: IN_TILT,  # path
        in_parts: IN_PARTICLES,  # path
    ):
        star = empty_star()

        opt_model = OptimisationSetModel(
            tomogram_star=self._check_and_normalize_path(in_mics),
            particles_star=self._check_and_normalize_path(in_parts),
        )
        star.with_loop_block(
            "optimisation_set", opt_model.block.trust_loop().to_pandas()
        )
        out_path = self.output_job_dir.path / "optimisation_set.star"
        star.write(out_path)
        self.console.log(f"Wrote output file to {out_path}")

    def _check_and_normalize_path(self, path: str) -> str:
        in_path = Path(path)
        if not in_path.exists():
            raise FileNotFoundError(f"Input file {path!r} not found.")
        in_path = in_path.resolve()
        rln_dir = self.output_job_dir.relion_project_dir
        if in_path.is_relative_to(rln_dir):
            in_path = in_path.relative_to(rln_dir)
        return str(in_path)


def _get_particle(path: Path) -> str:
    opt = OptimisationSetModel.validate_file(path / "run_optimisation_set.star")
    return opt.particles_star


def _get_mic(path: Path) -> str:
    opt = OptimisationSetModel.validate_file(path / "run_optimisation_set.star")
    return opt.tomogram_star


def _get_tomo_star_from_inspect(path: Path) -> str:
    opt = OptimisationSetModel.validate_file(path / "optimisation_set.star")
    return opt.tomogram_star


connect_jobs(
    SelectClassesInteractiveJob,
    InspectParticles,
    node_mapping={
        SelectClassesInteractiveJob._search_mics: "in_mics",
        "particles.star": "in_parts",
    },
)

connect_jobs(
    SelectSplitJob,
    InspectParticles,
    node_mapping={"particles_split1.star": "in_parts"},
)

connect_jobs(
    SelectRemoveDuplicatesJob,
    InspectParticles,
    node_mapping={"particles.star": "in_parts"},
)

connect_jobs(
    Refine3DTomoJob,
    InspectParticles,
    node_mapping={_get_mic: "in_mics", _get_particle: "in_parts"},
)
connect_jobs(
    InspectParticles,
    ExtractParticlesTomoJob,
    node_mapping={"optimisation_set.star": "in_optim.in_optimisation"},
)
connect_jobs(
    ExtractParticlesTomoJob,
    InspectParticles,
    node_mapping={
        "particles.star": "in_parts",
        _get_tomo_star_from_inspect: "in_mics",
    },
)
connect_jobs(
    InspectParticles,
    InitialModelTomoJob,
    node_mapping={
        "optimisation_set.star": "in_optim.in_optimisation",
    },
)
connect_jobs(
    InspectParticles,
    ReconstructParticlesJob,
    node_mapping={
        "optimisation_set.star": "in_optim.in_optimisation",
    },
)
connect_jobs(
    InspectParticles,
    Class3DTomoJob,
    node_mapping={
        "optimisation_set.star": "in_optim.in_optimisation",
    },
)
connect_jobs(
    InspectParticles,
    Refine3DTomoJob,
    node_mapping={
        "optimisation_set.star": "in_optim.in_optimisation",
    },
)
