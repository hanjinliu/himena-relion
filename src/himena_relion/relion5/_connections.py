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
    _spa.AutoPickTemplate2DJob,
    _spa.AutoPickTemplate3DJob,
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

connect_jobs(
    _spa.ExtractJob,
    _spa.InitialModelJob,
    node_mapping={"particles.star": "fn_img"},
)
connect_jobs(
    _spa.ReExtractJob,
    _spa.InitialModelJob,
    node_mapping={"particles.star": "fn_img"},
)
connect_jobs(
    _spa.ReExtractJob,
    _spa.Refine3DJob,
    node_mapping={"particles.star": "fn_img"},
)


def _optimiser_last_iter(path: Path) -> str:
    files = sorted(path.glob("run_it???_optimiser.star"))
    return str(files[-1]) if files else ""


def _particles_last_iter(path: Path) -> str:
    files = sorted(path.glob("run_it???_data.star"))
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
    _spa.SelectClassesInteractiveJob, _spa.InitialModelJob, {"particles.star": "fn_img"}
)
for class3d_job in [_spa.Class3DJob, _spa.Class3DNoAlignmentJob]:
    connect_jobs(
        _spa.InitialModelJob,
        class3d_job,
        {
            _particles_last_iter: "fn_img",
            "initial_model.mrc": "fn_ref",
        },
    )
    connect_jobs(
        class3d_job,
        _spa.SelectClassesInteractiveJob,
        node_mapping={_optimiser_last_iter: "fn_classes"},
    )
    connect_jobs(
        class3d_job,
        _spa.Refine3DJob,
        node_mapping={"run_class001.mrc": "fn_ref"},
    )
    connect_jobs(
        class3d_job,
        _spa.AutoPickTemplate3DJob,
        node_mapping={"run_class001.mrc": "fn_ref3d_autopick"},
    )
# TODO: implement the way to fill input_micrographs.
connect_jobs(
    _spa.InitialModelJob,
    _spa.AutoPickTemplate3DJob,
    node_mapping={"initial_model.mrc": "fn_ref3d_autopick"},
)
connect_jobs(
    _spa.Refine3DJob,
    _spa.AutoPickTemplate3DJob,
    node_mapping={"run_class001.mrc": "fn_ref3d_autopick"},
)
connect_jobs(
    _spa.InitialModelJob,
    _spa.Refine3DJob,
    {
        _particles_last_iter: "fn_img",
        "initial_model.mrc": "fn_ref",
    },
)
connect_jobs(
    _spa.SelectClassesInteractiveJob, _spa.Refine3DJob, {"particles.star": "fn_img"}
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


def mask_create_search_halfmap(path: Path) -> str | None:
    parents = JobDirectory(path).parent_jobs()
    for p in parents:
        type_label = p.job_type_label()
        if type_label.startswith("relion.refine3d"):
            half_map_path = p.path / "run_half1_class001_unfil.mrc"
            if half_map_path.exists():
                return str(half_map_path)
        elif type_label == "relion.reconstructparticletomo":
            half_map_path = p.path / "half1.mrc"
            if half_map_path.exists():
                return str(half_map_path)
    return None


def postprocess_search_particles(path: Path) -> str | None:
    parents = JobDirectory(path).parent_jobs()
    for p in parents:
        type_label = p.job_type_label()
        if type_label.startswith("relion.refine3d"):
            particles_path = p.path / "run_data.star"
            if particles_path.exists():
                return str(particles_path)
    return None


connect_jobs(
    _spa.MaskCreationJob,
    _spa.PostProcessJob,
    node_mapping={
        mask_create_search_halfmap: "fn_in",
        "mask.mrc": "fn_mask",
    },
)

connect_jobs(
    _spa.PostProcessJob,
    _spa.CtfRefineJob,
    node_mapping={
        postprocess_search_particles: "fn_data",
        "postprocess.star": "fn_post",
    },
)
