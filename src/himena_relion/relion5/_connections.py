from pathlib import Path

import mrcfile
from himena_relion._job_class import connect_jobs
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5 import _builtins as _spa
from himena_relion.schemas import ModelClasses


def inherit_particle_diameter(path: Path) -> float:
    """Inherit particle diameter from the previous job."""
    jobdir = JobDirectory(path)
    dia = jobdir.get_job_param("particle_diameter")
    return round(float(dia), 1)


connect_jobs(
    _spa.ImportMoviesJob,
    _spa.MotionCorr2Job,
    node_mapping={"movies.star": "input_star_mics"},
)
connect_jobs(
    _spa.ImportMoviesJob,
    _spa.MotionCorrOwnJob,
    node_mapping={"movies.star": "input_star_mics"},
)
connect_jobs(
    _spa.ImportMicrographsJob,
    _spa.CtfEstimationJob,
    node_mapping={"micrographs.star": "input_star_mics"},
)
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
    _spa.MotionCorrOwnJob,
    _spa.SelectMicrographsJob,
    node_mapping={"corrected_micrographs.star": "fn_mic"},
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
    _spa.SelectMicrographsJob,
    _spa.ManualPickJob,
    node_mapping={"micrographs.star": "fn_in"},
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
        _spa.SelectMicrographsJob,
        autopick_job,
        node_mapping={"micrographs.star": "fn_input_autopick"},
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
        _spa.JoinMicrographsJob,
        autopick_job,
        node_mapping={"join_micrographs.star": "fn_input_autopick"},
    )

connect_jobs(
    _spa.AutoPickTopazTrain,
    _spa.AutoPickTopazPick,
    node_mapping={"model_epoch9.sav": "topaz_model"},
)

for extract_job in [_spa.ExtractJob, _spa.ReExtractJob]:
    connect_jobs(
        extract_job,
        _spa.Class2DJob,
        node_mapping={"particles.star": "fn_img"},
    )
    connect_jobs(
        extract_job,
        _spa.InitialModelJob,
        node_mapping={"particles.star": "fn_img"},
    )
    connect_jobs(
        extract_job,
        _spa.SelectSplitJob,
        node_mapping={"particles.star": "fn_data"},
    )
connect_jobs(
    _spa.ReExtractJob,
    _spa.Refine3DJob,
    node_mapping={"particles.star": "fn_img"},
)
connect_jobs(
    _spa.Refine3DJob,
    _spa.ReExtractJob,
    node_mapping={"run_data.star": "fndata_reextract"},
)


def get_nr_iter(path: Path) -> int | None:
    """Get the final number of iterations from the job.star file."""
    params = JobDirectory(path).get_job_params_as_dict()
    if "nr_iter" in params:
        return int(params["nr_iter"])
    elif params.get("do_em", "No") == "Yes":
        return int(params["nr_iter_em"])
    elif params.get("do_grad", "No") == "Yes":
        return int(params["nr_iter_grad"])
    return None


def _optimiser_last_iter(path: Path) -> str:
    niter = get_nr_iter(path)
    if niter is None:
        return ""
    return path / f"run_it{niter:03d}_optimiser.star"


def run_class001_last_iter(path: Path) -> str:
    niter = get_nr_iter(path)
    if niter is None:
        return ""
    return path / f"run_it{niter:03d}_class001.mrc"


def _particles_last_iter(path: Path) -> str:
    niter = get_nr_iter(path)
    if niter is None:
        return ""
    return path / f"run_it{niter:03d}_data.star"


def _get_template_for_pick(path: Path) -> str:
    job_dir = JobDirectory(path)
    class_avg_path = job_dir.path.joinpath("class_averages.star")
    model = ModelClasses.validate_file(class_avg_path)
    class_mrcs_path = model.ref_image[0].split("@")[1]
    return job_dir.make_relative_path(job_dir.resolve_path(class_mrcs_path))


def _get_angpix_from_template_pick(path: Path) -> float | None:
    job_dir = JobDirectory(path)
    path_refs = _get_template_for_pick(path)
    path = job_dir.resolve_path(path_refs)
    with mrcfile.open(path, header_only=True) as mrc:
        return round(float(mrc.voxel_size.x), 3)


def _make_get_template_angpix(filename: str):
    def _func(path: Path) -> float | None:
        with mrcfile.open(path / filename, header_only=True) as mrc:
            return round(float(mrc.voxel_size.x), 3)

    return _func


for sel_class_job in [_spa.SelectClassesInteractiveJob, _spa.SelectClassesAutoJob]:
    connect_jobs(
        _spa.Class2DJob,
        sel_class_job,
        node_mapping={_optimiser_last_iter: "fn_model"},
    )
    connect_jobs(
        sel_class_job,
        _spa.Class2DJob,
        node_mapping={"particles.star": "fn_img"},
    )
    connect_jobs(
        sel_class_job,
        _spa.ReExtractJob,
        node_mapping={"particles.star": "fn_data_reextract"},
    )
    connect_jobs(
        sel_class_job,
        _spa.AutoPickTemplate2DJob,
        node_mapping={
            "class_averages.star": "fn_refs_autopick",
        },
        value_mapping={
            _get_angpix_from_template_pick: "angpix_ref",
        },
    )
    connect_jobs(
        sel_class_job,
        _spa.InitialModelJob,
        node_mapping={"particles.star": "fn_img"},
    )
    connect_jobs(
        sel_class_job,
        _spa.Refine3DJob,
        node_mapping={"particles.star": "fn_img"},
    )

for class3d_job in [_spa.Class3DJob, _spa.Class3DNoAlignmentJob]:
    connect_jobs(
        _spa.InitialModelJob,
        class3d_job,
        node_mapping={
            _particles_last_iter: "fn_img",
            "initial_model.mrc": "fn_ref",
        },
        value_mapping={inherit_particle_diameter: "particle_diameter"},
    )
    connect_jobs(
        class3d_job,
        _spa.SelectClassesInteractiveJob,
        node_mapping={_optimiser_last_iter: "fn_model"},
    )
    connect_jobs(
        class3d_job,
        _spa.Refine3DJob,
        node_mapping={run_class001_last_iter: "fn_ref"},
        value_mapping={inherit_particle_diameter: "particle_diameter"},
    )
    connect_jobs(
        _spa.Refine3DJob,
        class3d_job,
        node_mapping={"run_data.star": "fn_img", "run_class001.mrc": "fn_ref"},
        value_mapping={inherit_particle_diameter: "particle_diameter"},
    )
    connect_jobs(
        class3d_job,
        _spa.AutoPickTemplate3DJob,
        node_mapping={run_class001_last_iter: "fn_ref3d_autopick"},
        value_mapping={_make_get_template_angpix("run_class001.mrc"): "angpix_ref"},
    )

connect_jobs(
    _spa.InitialModelJob,
    _spa.AutoPickTemplate3DJob,
    node_mapping={"initial_model.mrc": "fn_ref3d_autopick"},
    value_mapping={_make_get_template_angpix("initial_model.mrc"): "angpix_ref"},
)
connect_jobs(
    _spa.Refine3DJob,
    _spa.AutoPickTemplate3DJob,
    node_mapping={"run_class001.mrc": "fn_ref3d_autopick"},
    value_mapping={_make_get_template_angpix("run_class001.mrc"): "angpix_ref"},
)
connect_jobs(
    _spa.InitialModelJob,
    _spa.Refine3DJob,
    node_mapping={
        _particles_last_iter: "fn_img",
        "initial_model.mrc": "fn_ref",
    },
    value_mapping={inherit_particle_diameter: "particle_diameter"},
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
connect_jobs(
    _spa.JoinParticlesJob,
    _spa.InitialModelJob,
    node_mapping={"join_particles.star": "fn_img"},
)
connect_jobs(
    _spa.JoinMoviesJob,
    _spa.MotionCorr2Job,
    node_mapping={"join_movies.star": "input_star_mics"},
)
connect_jobs(
    _spa.JoinMoviesJob,
    _spa.MotionCorrOwnJob,
    node_mapping={"join_movies.star": "input_star_mics"},
)
connect_jobs(
    _spa.JoinMicrographsJob,
    _spa.CtfEstimationJob,
    node_mapping={"join_micrographs.star": "input_star_mics"},
)
connect_jobs(
    _spa.JoinMicrographsJob,
    _spa.ManualPickJob,
    node_mapping={"join_micrographs.star": "fn_in"},
)
connect_jobs(
    _spa.Refine3DJob,
    _spa.BayesianPolishTrainJob,
    node_mapping={"run_data.star": "fn_data"},
)
connect_jobs(
    _spa.Refine3DJob,
    _spa.BayesianPolishJob,
    node_mapping={"run_data.star": "fn_data"},
)
connect_jobs(
    _spa.CtfRefineJob,
    _spa.BayesianPolishTrainJob,
    node_mapping={"particles_ctf_refine.star": "fn_data"},
)
connect_jobs(
    _spa.CtfRefineJob,
    _spa.BayesianPolishJob,
    node_mapping={"particles_ctf_refine.star": "fn_data"},
)


def mask_create_search_halfmap(path: Path) -> str | None:
    parents = JobDirectory(path).parent_jobs()
    for p in parents:
        type_label = p.job_type_label()
        if type_label.startswith("relion.refine3d"):
            # NOTE: don't add exists() check here, because the file may not be ready
            # if the job is still running. Same for below.
            half_map_path = p.path / "run_half1_class001_unfil.mrc"
            return str(half_map_path)
        elif type_label == "relion.reconstructparticletomo":
            half_map_path = p.path / "half1.mrc"
            return str(half_map_path)
    return None


def postprocess_search_particles(path: Path) -> str | None:
    parents = JobDirectory(path).parent_jobs()
    for p in parents:
        type_label = p.job_type_label()
        if type_label.startswith("relion.refine3d"):
            particles_path = p.path / "run_data.star"
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


def _ctf_refine_postprocess_star(path: Path) -> str:
    return JobDirectory(path).get_job_param("fn_post")


connect_jobs(
    _spa.CtfRefineJob,
    _spa.CtfRefineJob,
    node_mapping={
        "particles_ctf_refine.star": "fn_data",
        _ctf_refine_postprocess_star: "fn_post",
    },
)

connect_jobs(
    _spa.CtfRefineJob,
    _spa.Refine3DJob,
    node_mapping={"particles_ctf_refine.star": "fn_img"},
)
