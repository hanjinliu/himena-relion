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
    # job.star vs params converted from Python to job.star
    assert_param_name_match(params.keys(), params_back.keys())

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
    # run() vs params loaded from job.star to Python
    assert_param_name_match(job_cls._signature().parameters.keys(), params_py.keys())
    params_back = job_cls_ins.normalize_kwargs(**params_py)
    # job.star vs params converted from Python to job.star
    assert_param_name_match(params.keys(), params_back.keys())

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
