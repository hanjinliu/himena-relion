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


def _not_in_job_star(job_cls) -> tuple[str, ...]:
    """Parameters of run() that are intentionally not written in job.star."""
    from himena_relion import hijack

    if hijack.has_hijacker(job_cls.type_label()):
        return (hijack.USE_RELION_GUI,)
    return ()


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
    assert isinstance(job_cls_ins.status_tip(), str)
    assert not job_cls_ins.job_is_tomo()

    model = JobStarModel.validate_file(job_dir.job_star())
    params = model.joboptions_values.to_dict()
    params_py = job_cls_ins.normalize_kwargs_inv(**params)
    if job_cls_ins.type_label() == "relion.autopick.topaz.train":
        allowed_diffs = ("other_args",)
    else:
        allowed_diffs = ()
    allowed_diffs += _not_in_job_star(job_cls)

    # run() vs params loaded from job.star to Python
    assert_param_name_match(job_cls._signature().parameters.keys(), params_py.keys(), allowed_diffs)
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
    assert isinstance(job_cls_ins.status_tip(), str)
    # assert job_cls_ins.job_is_tomo()

    model = JobStarModel.validate_file(job_dir.job_star())
    params = model.joboptions_values.to_dict()
    params_py = job_cls_ins.normalize_kwargs_inv(**params)
    # these are needed for compatibility with RELION 5.0 and 5.1
    if job_cls_ins.type_label() == "relion.aligntiltseries":
        allowed_diffs = ("aretomo_OutBin", "do_aretomo_reconstruct", "aretomo_VolZ")
    elif job_cls_ins.type_label() == "relion.pseudosubtomo":
        allowed_diffs = ("do_stack2d",)
    else:
        allowed_diffs = ()
    allowed_diffs += _not_in_job_star(job_cls)
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

def test_class_ranker_has_no_recenter_regroup(himena_ui):
    """relion_class_ranker does not support recentering/regrouping (RELION refuses
    to create the job), so they must be "No" in job.star."""
    from himena_relion.relion5._builtins import SelectClassesAutoJob

    params = SelectClassesAutoJob._signature().parameters
    assert "do_recenter" not in params
    assert "do_regroup" not in params
    job_star = SelectClassesAutoJob.prep_job_star(fn_model="Class2D/job009/run_it025_optimiser.star")
    values = job_star.joboptions_values.to_dict()
    assert values["do_class_ranker"] == "Yes"
    assert values["do_recenter"] == "No"
    assert values["do_regroup"] == "No"


@pytest.mark.parametrize(
    "nr_groups, do_regroup, nr_groups_star",
    [(None, "No", "1"), (5, "Yes", "5")],
)
def test_select_interactive_regroup_param(
    himena_ui, tmp_path, nr_groups, do_regroup, nr_groups_star
):
    """do_regroup is not a parameter in GUI. It is "Yes" only when nr_groups is given."""
    from himena_relion.relion5._builtins import SelectClassesInteractiveJob
    from himena_relion.relion5._continues import SelectClassesInteractiveContinue

    job_cls = SelectClassesInteractiveJob
    assert "do_regroup" not in job_cls._signature().parameters
    job_star = job_cls.prep_job_star(
        fn_model="Class2D/job009/run_it025_optimiser.star", nr_groups=nr_groups
    )
    values = job_star.joboptions_values.to_dict()
    assert values["do_regroup"] == do_regroup
    assert values["nr_groups"] == nr_groups_star
    # job.star -> python
    params_py = job_cls.normalize_kwargs_inv(**values)
    assert "do_regroup" not in params_py
    assert params_py["nr_groups"] == (None if nr_groups is None else nr_groups_star)

    # continue job can change the regrouping
    job_dir = tmp_path / "Select" / "job010"
    job_dir.mkdir(parents=True)
    job_star.to_star_dict().write(job_dir / "job.star", newline="\n")
    cont = SelectClassesInteractiveContinue(JobDirectory(job_dir))
    new_nr_groups = 3 if nr_groups is None else None
    values_cont = cont.make_job_star(nr_groups=new_nr_groups).joboptions_values.to_dict()
    assert values_cont["do_regroup"] == ("Yes" if new_nr_groups else "No")
    assert values_cont["nr_groups"] == ("3" if new_nr_groups else "1")
    assert values_cont["fn_model"] == "Class2D/job009/run_it025_optimiser.star"


def test_hijacked_jobs_have_use_relion_gui(himena_ui):
    """Jobs that can be run by himena-relion have the "Use RELION GUI" toggle."""
    from himena.qt.magicgui import ToggleSwitch
    from himena_relion import hijack
    from himena_relion._job_class import iter_relion_jobs
    from himena_relion.relion5._builtins import SelectClassesInteractiveJob

    job_classes = []
    for job_cls in iter_relion_jobs():
        if job_cls.__name__.startswith("_"):
            continue
        try:
            type_label = job_cls.type_label()
        except Exception:
            continue
        if hijack.has_hijacker(type_label):
            job_classes.append(job_cls)
    assert {c.__name__ for c in job_classes} == {
        "SelectClassesInteractiveJob",
        "SelectClassesInteractiveContinue",
    }
    for job_cls in job_classes:
        param = job_cls._signature().parameters[hijack.USE_RELION_GUI]
        assert param.default is False  # run in himena-relion by default
        scheduler = QJobScheduler(himena_ui)
        scheduler.update_by_job(job_cls)
        toggle = scheduler._job_param_widget._mgui_widgets[hijack.USE_RELION_GUI]
        assert isinstance(toggle, ToggleSwitch)
        assert toggle.label == "Use RELION GUI"

    # not written in job.star
    for use_relion_gui in [False, True]:
        job_star = SelectClassesInteractiveJob.prep_job_star(
            fn_model="Class2D/job009/run_it025_optimiser.star",
            use_relion_gui=use_relion_gui,
        )
        assert hijack.USE_RELION_GUI not in job_star.joboptions_values.to_dict()
