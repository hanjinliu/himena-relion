"""Schedule every job type in a project managed by the emulated `relion_pipeliner`."""

import shutil
from pathlib import Path
from typing import Any

import pytest
from himena import MainWindow
from himena.plugins import when_reader_used
from himena.workflow import LocalReaderMethod

from himena_relion import _configs, _job_class
from himena_relion._job_class import RelionJob, _Relion5BuiltinContinue
from himena_relion._job_dir import JobDirectory
from himena_relion.consts import Type
from himena_relion.external import RelionExternalJob
from himena_relion.relion5._builtins import ImportMoviesJob
from himena_relion.schemas import JobStarModel

from ._fake_relion import (
    FakeRelionPipeliner,
    check_scheduled_jobs,
    default_kwargs,
    input_edges,
    read_pipeline,
    start_new_project,
    statuses,
)

IMPORT_JOB = "Import/job001/"
MOVIES_STAR = "Import/job001/movies.star"
_HALF_MAP = "Refine3D/job099/run_half1_class001_unfil.mrc"
_MASK = "MaskCreate/job099/mask.mrc"
# Parameters that must be given to schedule the jobs.
_REQUIRED = {
    "input_star_mics": MOVIES_STAR,
    "fn_input_autopick": MOVIES_STAR,
    "fn_opt": "Refine3D/job099/run_it010_optimiser.star",
    "fn_refs_autopick": "Select/job099/class_averages.star",
    "fn_ref3d_autopick": "Refine3D/job099/run_class001.mrc",
    "topaz_train_picks": "ManualPick/job099/manualpick.star",
    "fn_model": "Class2D/job099/run_it025_optimiser.star",
    "fn_data": "Extract/job099/particles.star",
}
_REQUIRED_BY_CLASS = {
    "PostProcessJob": {"fn_in": _HALF_MAP, "fn_mask": _MASK},
    "PostProcessTomoJob": {"fn_in": _HALF_MAP, "fn_mask": _MASK},
    "ParticleSubtractionJob": {"fn_mask": _MASK},
    "SelectSplitJob": {"nr_split": 2},
    "SelectMicrographsJob": {"fn_data": "", "fn_mic": MOVIES_STAR},
    "MaskCreationJob": {"fn_in": "Refine3D/job099/run_class001.mrc"},
}


def _builtin_job_classes() -> list[type[RelionJob]]:
    out = []
    for cls in _job_class.iter_relion_jobs():
        if issubclass(cls, (_Relion5BuiltinContinue, RelionExternalJob)):
            continue
        if cls.__module__.endswith("._builtins") and cls not in out:
            out.append(cls)
    return out


def _continue_job_classes() -> list[type[_Relion5BuiltinContinue]]:
    out = []
    for cls in _job_class.iter_relion_jobs():
        if issubclass(cls, _Relion5BuiltinContinue) and cls not in out:
            out.append(cls)
    return out


def _kwargs_for(job_cls: type[RelionJob]) -> dict[str, Any]:
    """The parameters the scheduler widget would give for a new job."""
    kwargs = default_kwargs(job_cls)
    for name in job_cls._signature().parameters:
        if name in _REQUIRED and kwargs[name] == "":
            kwargs[name] = _REQUIRED[name]
    kwargs.update(_REQUIRED_BY_CLASS.get(job_cls.__name__, {}))
    return kwargs


def _suggestions(job_dir: JobDirectory):
    """Iterate over (command ID, context) suggested from the job."""
    model_type = job_dir.himena_model_type()
    reg = when_reader_used(model_type)._registry
    meth = LocalReaderMethod(output_model_type=model_type, path=job_dir.path)
    for suggest in reg.iter_suggestion(model_type, meth):
        yield suggest, meth


def test_schedule_all_builtin_jobs(
    himena_ui: MainWindow, in_project: Path, relion: FakeRelionPipeliner, monkeypatch
):
    # external programs and directories in the config are not installed
    monkeypatch.setattr(shutil, "which", lambda cmd, *_, **__: str(cmd))
    monkeypatch.setattr(_configs, "get_cryocare_dir", lambda: str(in_project))

    start_new_project(himena_ui, in_project)
    ImportMoviesJob.create_job(_cwd=in_project, **default_kwargs(ImportMoviesJob))
    check_scheduled_jobs(in_project)
    relion.finish(IMPORT_JOB)
    assert statuses(read_pipeline(in_project)) == {IMPORT_JOB: "Succeeded"}

    job_classes = _builtin_job_classes()
    assert len(job_classes) > 50
    scheduled: dict[str, type[RelionJob]] = {}
    for job_cls in job_classes:
        name = job_cls.__name__
        job_path = job_cls.create_job(_cwd=in_project, **_kwargs_for(job_cls))
        pipeline = read_pipeline(in_project)
        job_id = pipeline.processes.process_name[-1]
        assert job_id not in scheduled, name
        scheduled[job_id] = job_cls
        assert statuses(pipeline)[job_id] == "Scheduled", name
        job_dir = JobDirectory(in_project / job_id)

        # the job is dispatched to the class that created it
        assert job_dir._to_job_class() is job_cls, name
        assert job_dir.job_title() == job_cls.job_title(), name
        model_type = f"{Type.RELION_JOB}.{job_cls.himena_model_type()}"
        assert job_dir.himena_model_type() == model_type, name
        job_star = JobStarModel.validate_file(job_dir.job_star())
        assert job_star.job.job_type_label == job_cls.type_label(), name
        assert bool(job_star.job.job_is_tomo) == job_cls.job_is_tomo(), name
        assert job_star.job.job_is_continue == 0, name

        # job.star can be converted back to the arguments
        params = job_dir.get_job_params_as_dict()
        kwargs = job_cls._parse_args(job_cls.normalize_kwargs_inv(**params))
        assert set(kwargs) == set(job_cls._signature().parameters), name
        edges = {e.strip() for e in job_cls(job_dir).input_edges(**params)} - {""}
        edges_in_pipeline = {n for n, job in input_edges(pipeline) if job == job_id}
        assert edges == edges_in_pipeline, name
        # the path is returned only if the job can be run immediately
        if job_path is None:
            assert edges - {MOVIES_STAR}, name
        else:
            assert job_path == job_dir.path, name
            assert not any("/job099/" in e for e in edges), name

    # Run the jobs. Jobs of the unknown parents are waited.
    check_scheduled_jobs(in_project)
    status = statuses(read_pipeline(in_project))
    for job_id, job_cls in scheduled.items():
        edges = {n for n, job in input_edges(read_pipeline(in_project)) if job == job_id}
        if any("/job099/" in e for e in edges):
            assert status[job_id] == "Scheduled", job_cls.__name__
        elif edges <= {MOVIES_STAR}:
            assert status[job_id] == "Running", job_cls.__name__
            is_hijacked = job_id not in relion.run_calls
            marker = in_project / job_id / "USE_HIMENA_IMPL"
            assert marker.exists() == is_hijacked, job_cls.__name__

    # Next jobs are suggested from each job.
    n_suggestions = 0
    for job_id, job_cls in scheduled.items():
        for suggest, meth in _suggestions(JobDirectory(in_project / job_id)):
            context = suggest.user_context(himena_ui, meth)
            assert isinstance(context, dict), (job_cls.__name__, suggest.command_id)
            # the scheduler is opened with the suggested parameters
            suggest.execute(himena_ui, meth)
            n_suggestions += 1
    assert n_suggestions > 100

    # Continue the jobs.
    job_ids = {job_cls: job_id for job_id, job_cls in scheduled.items()}
    continue_classes = _continue_job_classes()
    assert len(continue_classes) > 20
    n_checked = n_suggested = 0
    for cont_cls in continue_classes:
        name = cont_cls.__name__
        job_id = job_ids[cont_cls.original_class]
        job_dir = JobDirectory(in_project / job_id)
        edges = {n for n, job in input_edges(read_pipeline(in_project)) if job == job_id}
        scheduler = cont_cls._show_scheduler_widget_for_continue(
            himena_ui, {_job_class._JOB_DIR_ARGS_NAME: job_dir}
        )
        params = scheduler.get_parameters()
        if "fn_cont" in params:
            # most jobs need the optimiser.star file to continue from
            try:
                cont_cls(job_dir).continue_job(**params)
            except ValueError as e:
                assert "Continue from here" in str(e), name
                assert statuses(read_pipeline(in_project))[job_id] != "Scheduled", name
                n_checked += 1
            job_dir.path.joinpath("run_it005_optimiser.star").write_text("")
            (context,) = (
                suggest.user_context(himena_ui, meth)
                for suggest, meth in _suggestions(job_dir)
                if suggest.command_id == cont_cls.command_id()
            )
            fn_cont = f"{job_id}run_it005_optimiser.star"
            # the latest file is suggested (not for MultiBody)
            assert context.get("fn_cont", fn_cont) == fn_cont, name
            n_suggested += "fn_cont" in context
            params["fn_cont"] = fn_cont
        cont_cls(job_dir).continue_job(**params)
        job_star = JobStarModel.validate_file(job_dir.job_star())
        assert job_star.job.job_is_continue == 1, name
        assert job_star.job.job_type_label == cont_cls.original_class.type_label(), name
        pipeline = read_pipeline(in_project)
        assert statuses(pipeline)[job_id] == "Scheduled", name
        assert {n for n, job in input_edges(pipeline) if job == job_id} == edges, name
        # still dispatched to the original class
        assert job_dir._to_job_class() is cont_cls.original_class, name
    assert n_checked >= 8
    assert n_suggested >= 8


def test_jobs_with_invalid_inputs_are_not_scheduled(
    himena_ui: MainWindow, in_project: Path, relion: FakeRelionPipeliner, monkeypatch
):
    from himena_relion.relion5 import _builtins as _spa
    from himena_relion.relion5_tomo import _builtins as _tomo

    monkeypatch.setattr(shutil, "which", lambda cmd, *_, **__: str(cmd))
    monkeypatch.setattr(_configs, "get_cryocare_dir", lambda: str(in_project))
    start_new_project(himena_ui, in_project)
    mics = {"fn_input_autopick": "CtfFind/job003/micrographs_ctf.star"}
    cases = [
        (_spa.MotionCorrOwnJob, {}, "Input movies.star must be provided"),
        (_spa.MotionCorr2Job, {}, "Input movies.star must be provided"),
        (_tomo.MotionCorrOwnTomoJob, {}, "Input movies.star must be provided"),
        (_spa.CtfEstimationJob, {}, "Input micrographs.star must be provided"),
        (_spa.AutoPickLogJob, {}, "Input micrographs.star must be provided"),
        (_spa.AutoPickTemplate2DJob, mics, "2D reference"),
        (_spa.AutoPickTemplate3DJob, mics, "3D reference"),
        (_spa.AutoPickTopazTrain, mics, "picked coordinates for training"),
        (
            _spa.AutoPickTopazTrain,
            {**mics, "do_topaz_train_parts": True},
            "Particles STAR file for training",
        ),
        (_spa.SelectSplitJob, {"fn_data": "Extract/job004/particles.star"}, "nr_split"),
        (_spa.PostProcessJob, {"fn_in": "Refine3D/job005/run_class001.mrc"}, "half"),
        (_spa.PostProcessJob, {"fn_in": _HALF_MAP}, "Input mask must be provided"),
        (_tomo.PostProcessTomoJob, {"fn_in": _HALF_MAP}, "Input mask must be provided"),
        (_spa.ParticleSubtractionJob, {}, "Input optimiser.star must be provided"),
        (
            _spa.ParticleSubtractionJob,
            {"fn_opt": "Refine3D/job005/run_it010_optimiser.star"},
            "Input mask must be provided",
        ),
        (_tomo.DenoiseTrain, {"subvolume_dimensions": 60}, "divisible by 8"),
    ]
    for job_cls, kwargs, message in cases:
        with pytest.raises(ValueError, match=message):
            job_cls.create_job(_cwd=in_project, **default_kwargs(job_cls, **kwargs))
    # nothing was added to the project
    assert "data_pipeline_processes" not in relion.path.read_text()
    assert [p.name for p in in_project.iterdir() if p.is_dir()] == []

    # The external programs must be found before scheduling the jobs.
    monkeypatch.setattr(shutil, "which", lambda *_, **__: None)
    monkeypatch.setattr(_configs, "get_cryocare_dir", lambda: "/path/to/nothing")
    not_found = set()
    for job_cls in _builtin_job_classes():
        try:
            job_cls.prerun_check(**_kwargs_for(job_cls))
        except ValueError as e:
            assert "Please set a correct path in the config" in str(e)
            not_found.add(job_cls.__name__)
    assert not_found >= {
        "MotionCorr2Job",
        "MotionCorr2TomoJob",
        "CtfEstimationJob",
        "CtfEstimationTomoJob",
        "AutoPickTopazPick",
        "LocalResolutionResmapJob",
        "DynaMightJob",
        "ModelAngeloJob",
        "AlignTiltSeriesImodFiducial",
        "AlignTiltSeriesAreTomo2",
        "ReconstructTomoByAreTomo2",
        "DenoiseTrain",
        "DenoisePredict",
    }
    # jobs that only use RELION are not affected
    assert not not_found & {"ImportMoviesJob", "MotionCorrOwnJob", "Refine3DJob"}
