from pathlib import Path
from himena_relion._job_class import connect_jobs
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5 import _builtins as _spa

connect_jobs(
    _spa.MotionCorr2Job,
    _spa.CtfEstimationJob,
    node_mapping={"corrected_micrographs.star": "input_star_mics"},
)
connect_jobs(
    _spa.MotionCorrOwnJob,
    _spa.CtfEstimationJob,
    node_mapping={"corrected_micrographs.star": "input_star_mics"},
)
connect_jobs(
    _spa.CtfEstimationJob,
    _spa.SelectMicrographsJob,
    node_mapping={"micrographs_ctf.star": "fn_mic"},
)
connect_jobs(
    _spa.CtfEstimationJob,
    _spa.ManualPickJob,
    node_mapping={"micrographs_ctf.star": "fn_in"},
)
connect_jobs(
    _spa.ManualPickJob,
    _spa.ExtractJob,
    node_mapping={
        "micrographs_selected.star": "star_mics",
        "manualpick.star": "coords_suffix",
    },
)


# Autopick connections
def _get_micrograph_ctf_star(path: Path) -> str | None:
    pipeline = JobDirectory(path).parse_job_pipeline()
    if in0 := pipeline.get_input_by_type("MicrographGroupMetadata"):
        return str(in0.path)


for autopick_job in [
    _spa.AutoPickTemplateJob,
    _spa.AutoPickLogJob,
    _spa.AutoPickTopazTrain,
    _spa.AutoPickTopazPick,
]:
    connect_jobs(
        _spa.CtfEstimationJob,
        autopick_job,
        node_mapping={"micrographs_ctf.star": "fn_input_autopick"},
    )
    connect_jobs(
        autopick_job,
        _spa.ExtractJob,
        node_mapping={
            _get_micrograph_ctf_star: "star_mics",
            "autopick.star": "coords_suffix",
        },
    )


def _optimiser_last_iter(path: Path) -> str:
    files = sorted(path.glob("run_it???_optimiser.star"))
    return str(files[-1]) if files else ""


connect_jobs(
    _spa.Class2DJob,
    _spa.SelectClassesInteractiveJob,
    node_mapping={_optimiser_last_iter: "fn_classes"},
)
connect_jobs(
    _spa.Class2DJob,
    _spa.SelectClassesAutoJob,
    node_mapping={_optimiser_last_iter: "fn_classes"},
)
connect_jobs(
    _spa.SelectClassesInteractiveJob,
    _spa.InitialModelJob,
)
connect_jobs(
    _spa.Class3DJob,
    _spa.SelectClassesInteractiveJob,
    node_mapping={_optimiser_last_iter: "fn_classes"},
)
connect_jobs(
    _spa.Class3DJob,
    _spa.Refine3DJob,
    node_mapping={"run_class001.mrc": "fn_ref"},
)
connect_jobs(
    _spa.Refine3DJob,
    _spa.MaskCreationJob,
    node_mapping={"run_class001.mrc": "fn_in"},
)
connect_jobs(
    _spa.Refine3DJob,
    _spa.PostProcessJob,
    node_mapping={"run_half1_class001_unfil.mrc": "fn_in"},
)
