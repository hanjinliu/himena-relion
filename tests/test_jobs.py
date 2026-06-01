from contextlib import suppress
from pathlib import Path
from typing import Callable
from himena import MainWindow
import pytest
from himena_relion._widgets._job_edit import QJobScheduler
from himena_relion._job_dir import JobDirectory
from himena_relion.schemas import JobStarModel
from ._utils import (
    assert_param_name_match,
    iter_spa_job_dirs,
    iter_tomo_job_dirs,
    JOBS_DIR_SPA,
    JOBS_DIR_TOMO,
)

@pytest.mark.parametrize(
    "job_str",
    list(iter_spa_job_dirs())
)
def test_spa_job_match(job_str: str, make_himena_ui: Callable[[], MainWindow]):
    ui = make_himena_ui("mock")  # noqa: F841
    job_dir = JobDirectory(JOBS_DIR_SPA / job_str)
    job_cls = job_dir._to_job_class()
    assert job_cls is not None, f"Failed to determine job class for {job_str}"
    assert job_cls.type_label() == job_dir.job_type_label()

    job_cls_ins = job_cls(job_dir)
    assert isinstance(job_cls_ins.command_id(), str)
    assert isinstance(job_cls_ins.job_title(), str)
    assert isinstance(job_cls_ins.command_palette_title_prefix(), str)
    assert isinstance(job_cls_ins.himena_model_type(), str)
    assert not job_cls_ins.job_is_tomo()

    model = JobStarModel.validate_file(job_dir.job_star())
    params = model.joboptions_values.to_dict()
    params_py = job_cls_ins.normalize_kwargs_inv(**params)

    # run() vs params loaded from job.star to Python
    assert_param_name_match(job_cls._signature().parameters.keys(), params_py.keys())
    params_back = job_cls_ins.normalize_kwargs(**params_py)

    # check none of the parameters are None
    for k, v in params_back.items():
        assert v is not None, f"Parameter {k} is None in job {job_str}"

    # job.star vs params converted from Python to job.star
    assert_param_name_match(params.keys(), params_back.keys())

    # test input_edges method
    edges = job_cls_ins.input_edges(**job_dir.get_job_params_as_dict())
    assert isinstance(edges, list), f"input_edges should return a list, got {type(edges)}"
    for edge in edges:
        assert isinstance(edge, str), f"Each edge should be a string, got {type(edge)}"

@pytest.mark.parametrize(
    "job_str",
    list(iter_tomo_job_dirs())
)
def test_tomo_job_match(job_str: str, make_himena_ui: Callable[[], MainWindow]):
    ui = make_himena_ui("mock")  # noqa: F841
    job_dir = JobDirectory(JOBS_DIR_TOMO / job_str)
    job_cls = job_dir._to_job_class()
    assert job_cls is not None, f"Failed to determine job class for {job_str}"
    assert job_cls.type_label() == job_dir.job_type_label()

    job_cls_ins = job_cls(job_dir)
    assert isinstance(job_cls_ins.command_id(), str)
    assert isinstance(job_cls_ins.job_title(), str)
    assert isinstance(job_cls_ins.command_palette_title_prefix(), str)
    assert isinstance(job_cls_ins.himena_model_type(), str)
    # assert job_cls_ins.job_is_tomo()

    model = JobStarModel.validate_file(job_dir.job_star())
    params = model.joboptions_values.to_dict()
    params_py = job_cls_ins.normalize_kwargs_inv(**params)
    # these are needed for compatibility with RELION 5.0 and 5.1
    if job_cls_ins.type_label() == "relion.aligntiltseries":
        allowed_diffs = ("other_args", "aretomo_OutBin", "do_aretomo_reconstruct", "aretomo_VolZ")
    elif job_cls_ins.type_label() == "relion.pseudosubtomo":
        allowed_diffs = ("other_args", "do_stack2d")
    else:
        allowed_diffs = ("other_args",)
    # run() vs params loaded from job.star to Python
    assert_param_name_match(
        job_cls._signature().parameters.keys(),
        params_py.keys(),
        allowed_diffs=allowed_diffs,
    )
    params_back = job_cls_ins.normalize_kwargs(**params_py)

    # check none of the parameters are None
    for k, v in params_back.items():
        assert v is not None, f"Parameter {k} is None in job {job_str}"

    # job.star vs params converted from Python to job.star
    assert_param_name_match(params.keys(), params_back.keys())
    # test input_edges method
    edges = job_cls_ins.input_edges(**job_dir.get_job_params_as_dict())
    assert isinstance(edges, list), f"input_edges should return a list, got {type(edges)}"
    for edge in edges:
        assert isinstance(edge, str), f"Each edge should be a string, got {type(edge)}"

@pytest.mark.parametrize(
    "job_str",
    list(iter_spa_job_dirs())
)
def test_spa_set_job_param(job_str: str, make_himena_ui: Callable[[], MainWindow]):
    ui = make_himena_ui("mock")  # this is needed to get plugin config
    job_dir = JobDirectory(JOBS_DIR_SPA / job_str)
    job_cls = job_dir._to_job_class()
    assert job_cls is not None, f"Failed to determine job class for {job_str}"
    scheduler = QJobScheduler(ui)
    scheduler.update_by_job(job_cls)
    job_star_params = job_dir.get_job_params_as_dict()
    scheduler.set_parameters(job_star_params)

    params = scheduler.get_parameters()
    job_cls.prep_job_star(**params).to_string()
    with suppress(ValueError):
        job_cls.prerun_check(**params)

    # TODO: this is failing because not all the parameters are round-trippable.
    # For example, in import job, changing in_coords does not affect running import
    # movies job, so this parameter does not need to match.

    # job_star_model = job_cls.prep_job_star(**params)
    # job_star_from_scheduler = job_star_model.to_string()
    # job_star_rewrite = JobStarModel.validate_file(job_dir.job_star()).to_string()
    # assert job_star_from_scheduler == job_star_rewrite

@pytest.mark.parametrize(
    "job_str",
    list(iter_tomo_job_dirs())
)
def test_tomo_set_job_param(job_str: str, make_himena_ui: Callable[[], MainWindow]):
    ui = make_himena_ui("mock")  # this is needed to get plugin config
    job_dir = JobDirectory(JOBS_DIR_TOMO / job_str)
    job_cls = job_dir._to_job_class()
    assert job_cls is not None, f"Failed to determine job class for {job_str}"
    scheduler = QJobScheduler(ui)
    scheduler.update_by_job(job_cls)
    job_star_params = job_dir.get_job_params_as_dict()
    scheduler.set_parameters(job_star_params)

    params = scheduler.get_parameters()
    job_cls.prep_job_star(**params).to_string()

def test_job_class_parse_arg():
    from himena_relion.relion5.extensions.transform.jobs import ShiftMapJob

    args = ShiftMapJob._parse_args({"in_3dref": "ref.mrc", "center_by": "pixel"})
    assert args["in_3dref"] == "ref.mrc"
    assert args["center_by"] == "pixel"

def test_continue_job(
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
    himena_ui,
):
    from himena_relion.relion5._continues import Refine3DContinue

    star_text = Path(jobs_dir_spa / "Refine3D" / "job001" / "job.star").read_text()
    optimiser_star_path = "Refine3D/job025/run_it010_optimiser.star"
    lines = []
    for line in star_text.splitlines():
        if line.strip().startswith("fn_cont"):
            line = f"fn_cont   {optimiser_star_path}"
        lines.append(line)
    star_text = "\n".join(lines)
    job_dir = make_job_directory(star_text, "Refine3D")
    job_dir.relion_project_dir.joinpath(optimiser_star_path).write_text("")  # create the optimiser.star file
    ref_job = Refine3DContinue(job_dir)

    model = JobStarModel.validate_file(job_dir.job_star())
    output = ref_job.make_job_star()
    assert output.joboptions_values.dataframe.shape == model.joboptions_values.dataframe.shape
    assert output.joboptions_values.to_dict() != model.joboptions_values.to_dict(), "The continue job should update the parameters"
    params = model.joboptions_values.to_dict()
    assert "fn_cont" in params
    kwargs = ref_job.normalize_kwargs_inv(**params)
    ref_job.prerun_check(**kwargs)
