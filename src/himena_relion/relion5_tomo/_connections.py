from pathlib import Path

from himena_relion._job_dir import JobDirectory
from himena_relion.relion5 import _builtins as _spa
from himena_relion.relion5_tomo import _builtins as _tomo
from himena_relion._job_class import connect_jobs


def _optimiser_last_iter(path: Path) -> str:
    files = sorted(path.glob("run_it???_optimiser.star"))
    return str(files[-1]) if files else ""


def _box_size(path: Path) -> int:
    """Extract box size from the job directory path."""
    jobdir = JobDirectory(path)
    return int(jobdir.get_job_param("box_size"))


def _crop_size(path: Path) -> int:
    """Extract crop size from the job directory path."""
    jobdir = JobDirectory(path)
    return int(jobdir.get_job_param("crop_size"))


for _MotionCorJob in [_tomo.MotionCorr2TomoJob, _tomo.MotionCorrOwnTomoJob]:
    connect_jobs(
        _tomo.ImportTomoJob,
        _MotionCorJob,
        node_mapping={"tilt_series.star": "in_movies"},
    )
connect_jobs(
    _tomo.MotionCorr2TomoJob,
    _tomo.CtfEstimationTomoJob,
    node_mapping={"corrected_tilt_series.star": "input_star_mics"},
)
connect_jobs(
    _tomo.MotionCorrOwnTomoJob,
    _tomo.CtfEstimationTomoJob,
    node_mapping={"corrected_tilt_series.star": "input_star_mics"},
)
connect_jobs(
    _tomo.CtfEstimationTomoJob,
    _tomo.ExcludeTiltJob,
    node_mapping={"tilt_series_ctf.star": "in_tiltseries"},
)
for _AlignJob in [
    _tomo.AlignTiltSeriesImodFiducial,
    _tomo.AlignTiltSeriesImodPatch,
    _tomo.AlignTiltSeriesAreTomo2,
]:
    connect_jobs(
        _tomo.CtfEstimationTomoJob,
        _AlignJob,
        node_mapping={"tilt_series_ctf.star": "in_tiltseries"},
    )
    connect_jobs(
        _tomo.ExcludeTiltJob,
        _AlignJob,
        node_mapping={"selected_tilt_series.star": "in_tiltseries"},
    )
connect_jobs(
    _tomo.AlignTiltSeriesImodFiducial,
    _tomo.ReconstructTomogramJob,
    node_mapping={"aligned_tilt_series.star": "in_tiltseries"},
)
# connect_jobs(
#     AlignTiltSeriesImodPatch,
#     ReconstructTomogramJob,
#     node_mapping={"aligned_tilt_series.star": "in_tiltseries"},
# )
# connect_jobs(
#     AlignTiltSeriesAreTomo2,
#     ReconstructTomogramJob,
#     node_mapping={"aligned_tilt_series.star": "in_tiltseries"},
# )
connect_jobs(
    _tomo.ReconstructTomogramJob,
    _tomo.DenoiseTrain,
    node_mapping={"tomograms.star": "in_tomoset"},
)
connect_jobs(
    _tomo.DenoiseTrain,
    _tomo.DenoisePredict,
    node_mapping={"tomograms.star": "in_tomoset"},
)
connect_jobs(
    _tomo.ReconstructTomogramJob,
    _tomo.PickJob,
    node_mapping={"tomograms.star": "in_tomoset"},
)
connect_jobs(
    _tomo.DenoisePredict,
    _tomo.PickJob,
    node_mapping={"tomograms.star": "in_tomoset"},
)
connect_jobs(
    _tomo.PickJob,
    _tomo.ExtractParticlesTomoJob,
    node_mapping={"optimisation_set.star": "in_optim.in_optimisation"},
)
connect_jobs(
    _spa.SelectClassesInteractiveJob,
    _tomo.ExtractParticlesTomoJob,
)
connect_jobs(
    _spa.SelectSplitJob,
    _tomo.PickJob,
    node_mapping={
        "particles_split1.star": "fn_data",
    },
)
connect_jobs(
    _spa.SelectRemoveDuplicatesJob,
    _tomo.ReconstructParticlesJob,
)
connect_jobs(
    _tomo.PickJob,
    _spa.SelectSplitJob,
    node_mapping={"particles.star": "fn_data"},
)
connect_jobs(
    _tomo.ExtractParticlesTomoJob,
    _tomo.InitialModelTomoJob,
    node_mapping={
        "optimisation_set.star": "in_optim.in_optimisation",
    },
)
connect_jobs(
    _tomo.ExtractParticlesTomoJob,
    _tomo.ReconstructParticlesJob,
    node_mapping={
        "optimisation_set.star": "in_optim.in_optimisation",
    },
    value_mapping={
        _box_size: "box_size",
        _crop_size: "crop_size",
    },
)
connect_jobs(
    _tomo.InitialModelTomoJob,
    _tomo.Class3DTomoJob,
    node_mapping={
        "optimisation_set.star": "in_optim.in_optimisation",
        "initial_model.mrc": "fn_ref",
    },
)
connect_jobs(
    _tomo.InitialModelTomoJob,
    _tomo.Refine3DTomoJob,
    node_mapping={
        "optimisation_set.star": "in_optim.in_optimisation",
        "initial_model.mrc": "fn_ref",
    },
)
connect_jobs(
    _tomo.Class3DTomoJob,
    _tomo.Refine3DTomoJob,
)

connect_jobs(
    _tomo.Refine3DTomoJob,
    _spa.SelectRemoveDuplicatesJob,
    node_mapping={"run_data.star": "fn_data"},
)
connect_jobs(
    _tomo.Refine3DTomoJob,
    _spa.MaskCreationJob,
    node_mapping={"run_class001.mrc.star": "fn_in"},
)

connect_jobs(
    _tomo.Class3DTomoJob,
    _spa.SelectClassesInteractiveJob,
    node_mapping={_optimiser_last_iter: "fn_model"},
)

connect_jobs(
    _tomo.ReconstructParticlesJob,
    _tomo.Refine3DTomoJob,
    node_mapping={
        "optimisation_set.star": "in_optim.in_optimisation",
        "merged.mrc": "fn_ref",
    },
)
connect_jobs(
    _tomo.ReconstructParticlesJob,
    _tomo.PostProcessTomoJob,
    node_mapping={"half1.mrc": "fn_in"},
)
connect_jobs(
    _tomo.PostProcessTomoJob,
    _tomo.CtfRefineTomoJob,
    node_mapping={"postprocess.star": "in_post"},
)
connect_jobs(
    _tomo.CtfRefineTomoJob,
    _tomo.ReconstructParticlesJob,
    node_mapping={"optimisation_set.star": "in_optim.in_optimisation"},
)
connect_jobs(
    _tomo.CtfRefineTomoJob,
    _tomo.Refine3DTomoJob,
    node_mapping={"optimisation_set.star": "in_optim.in_optimisation"},
)
