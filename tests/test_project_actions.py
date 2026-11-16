"""Tests of the job operations in a project managed by the emulated `relion_pipeliner`.

See `_fake_relion.py` for the emulation.
"""

import subprocess
from pathlib import Path

import pytest
from himena import MainWindow
from himena.exceptions import Cancelled
from himena.testing import choose_one_dialog_response, user_string_input_response

from himena_relion import _job_class, pipeline_watcher
from himena_relion._job_dir import JobDirectory
from himena_relion._pipeline import ReadyState, is_all_inputs_ready
from himena_relion._widgets._job_edit import QJobScheduler
from himena_relion.consts import DEFAULT_PIPELINE_STAR, FileNames
from himena_relion.io import _impl
from himena_relion.relion5._builtins import ImportMoviesJob, MotionCorrOwnJob
from himena_relion.relion5._continues import MotionCorrOwnContinue
from himena_relion.schemas import JobStarModel, RelionPipelineModel

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
MOTIONCORR_JOB = "MotionCorr/job002/"
MOVIES_STAR = "Import/job001/movies.star"


def _create_import_job(rln_dir: Path) -> Path | None:
    return ImportMoviesJob.create_job(
        _cwd=rln_dir, **default_kwargs(ImportMoviesJob, fn_in_raw="Movies/*.tif")
    )


def _create_motioncorr_job(rln_dir: Path, input_star_mics: str = MOVIES_STAR):
    return MotionCorrOwnJob.create_job(
        _cwd=rln_dir,
        **default_kwargs(MotionCorrOwnJob, input_star_mics=input_star_mics),
    )


@pytest.fixture
def project(himena_ui: MainWindow, in_project: Path, relion: FakeRelionPipeliner):
    """Project with Import (finished) and MotionCorr (running) jobs."""
    start_new_project(himena_ui, in_project)
    _create_import_job(in_project)
    check_scheduled_jobs(in_project)
    relion.finish(IMPORT_JOB)
    _create_motioncorr_job(in_project)
    check_scheduled_jobs(in_project)
    assert statuses(read_pipeline(in_project)) == {
        IMPORT_JOB: "Succeeded",
        MOTIONCORR_JOB: "Running",
    }
    return in_project


def _status(rln_dir: Path, job_id: str) -> str:
    return statuses(read_pipeline(rln_dir))[job_id]


def test_job_commands(himena_ui: MainWindow, project: Path, relion, monkeypatch):
    job_win = himena_ui.read_file(project / MOTIONCORR_JOB)
    job_dir = job_win.value
    assert isinstance(job_dir, JobDirectory)
    assert job_dir.job_normal_id() == MOTIONCORR_JOB
    assert [p.job_normal_id() for p in job_dir.parent_jobs()] == [IMPORT_JOB]

    def _exec(command_id: str):
        himena_ui.current_window = job_win
        return himena_ui.exec_action(command_id)

    # open the files as text
    _exec("himena-relion:open-job-star")
    assert "relion.motioncorr.own" in himena_ui.current_model.value
    _exec("himena-relion:open-job-pipeline-star")
    assert MOVIES_STAR in himena_ui.current_model.value

    # relion_pipeliner is called to clean the job
    calls = []
    monkeypatch.setattr(
        _impl.subprocess, "run", lambda args, **kwargs: calls.append((args, kwargs))
    )
    _exec("himena-relion:gentle-clean")
    _exec("himena-relion:harsh-clean")
    assert [args[-2:] for args, _ in calls] == [
        ["--gentle_clean", "2"],
        ["--harsh_clean", "2"],
    ]
    assert all(kwargs["cwd"] == project for _, kwargs in calls)

    # the scheduler is filled with the parameters of the job
    for command_id in ["himena-relion:clone-job", "himena-relion:overwrite-job"]:
        _exec(command_id)
        scheduler = _job_class.scheduler_widget(himena_ui)
        assert isinstance(scheduler, QJobScheduler)
        assert scheduler.get_parameters()["input_star_mics"] == MOVIES_STAR

    # abort: cancelled, then aborted
    with choose_one_dialog_response(himena_ui, False):
        _exec("himena-relion:abort-job")
    assert not job_dir.path.joinpath(FileNames.ABORT_NOW).exists()
    with choose_one_dialog_response(himena_ui, True):
        _exec("himena-relion:abort-job")
    assert job_dir.path.joinpath(FileNames.ABORT_NOW).exists()

    # mark as failed / finished
    _exec("himena-relion:mark-as-failed")
    assert _status(project, MOTIONCORR_JOB) == "Failed"
    assert job_dir.path.joinpath(FileNames.EXIT_FAILURE).exists()
    assert not job_dir.path.joinpath(FileNames.ABORT_NOW).exists()
    _exec("himena-relion:mark-as-finished")
    assert _status(project, MOTIONCORR_JOB) == "Succeeded"
    assert job_dir.path.joinpath(FileNames.EXIT_SUCCESS).exists()
    assert not job_dir.path.joinpath(FileNames.EXIT_FAILURE).exists()
    _exec("himena-relion:mark-as-failed")
    assert not job_dir.path.joinpath(FileNames.EXIT_SUCCESS).exists()
    _exec("himena-relion:mark-as-finished")

    # finished jobs cannot be aborted
    with pytest.raises(RuntimeError, match="Cannot abort"):
        _impl.abort_relion_job(himena_ui, job_dir)


def test_job_parameters_window(himena_ui: MainWindow, project: Path):
    job_dir = JobDirectory(project / MOTIONCORR_JOB)
    n_windows = sum(len(tab) for tab in himena_ui.tabs)
    _impl.open_job_parameters(himena_ui, job_dir)
    assert sum(len(tab) for tab in himena_ui.tabs) == n_windows + 1
    assert himena_ui.current_window.title == f"Parameters of {MOTIONCORR_JOB}"


def test_set_alias_and_trash(himena_ui: MainWindow, project: Path, relion):
    relion.finish(MOTIONCORR_JOB)
    job_dir = JobDirectory(project / IMPORT_JOB)
    with user_string_input_response(himena_ui, "movies"):
        _impl.set_job_alias(himena_ui, job_dir)
    pipeline = read_pipeline(project)
    assert list(pipeline.processes.alias) == ["Import/movies/", "None"]
    job_pipeline = RelionPipelineModel.validate_file(job_dir.job_pipeline())
    assert list(job_pipeline.processes.alias) == ["Import/movies/"]
    link = project / "Import" / "movies"
    assert link.is_symlink()
    assert link.resolve() == job_dir.path

    # invalid aliases
    with user_string_input_response(himena_ui, None):
        with pytest.raises(Cancelled):
            _impl.set_job_alias(himena_ui, job_dir)
    for alias, error in [
        ("", ValueError),
        ("..", ValueError),
        ("movies", FileExistsError),
    ]:
        with user_string_input_response(himena_ui, alias):
            with pytest.raises(error):
                _impl.set_job_alias(himena_ui, job_dir)
    assert list(read_pipeline(project).processes.alias) == ["Import/movies/", "None"]

    # cancel trashing
    with choose_one_dialog_response(himena_ui, False):
        with pytest.raises(Cancelled):
            _impl.trash_job(himena_ui, job_dir)
    assert job_dir.path.exists()

    # the child job is also trashed, and the alias is removed
    himena_ui.read_file(project / MOTIONCORR_JOB)
    n_tabs = len(himena_ui.tabs)
    with choose_one_dialog_response(himena_ui, True):
        _impl.trash_job(himena_ui, job_dir)
    assert not project.joinpath(IMPORT_JOB).exists()
    assert not project.joinpath(MOTIONCORR_JOB).exists()
    assert not link.is_symlink()
    assert project.joinpath("Trash", MOTIONCORR_JOB, "job.star").exists()
    assert len(himena_ui.tabs) <= n_tabs

    # restore: jobs not in the trash are ignored
    _impl.restore_trashed_jobs(
        project, ["Import/job001", "MotionCorr/job002", "Extract/job099"]
    )
    pipeline = read_pipeline(project)
    assert statuses(pipeline) == {IMPORT_JOB: "Succeeded", MOTIONCORR_JOB: "Succeeded"}
    assert input_edges(pipeline) == [(MOVIES_STAR, MOTIONCORR_JOB)]
    assert not project.joinpath("Trash", "Import").exists()


def test_restore_job_with_alias_set_in_himena(himena_ui: MainWindow, project: Path):
    job_dir = JobDirectory(project / IMPORT_JOB)
    with user_string_input_response(himena_ui, "movies"):
        _impl.set_job_alias(himena_ui, job_dir)
    with choose_one_dialog_response(himena_ui, True):
        _impl.trash_job(himena_ui, job_dir)
    _impl.restore_trashed_jobs(project, ["Import/job001", "MotionCorr/job002"])
    assert list(read_pipeline(project).processes.alias) == ["Import/movies/", "None"]
    assert project.joinpath("Import", "movies").is_symlink()
    assert not project.joinpath("movies").exists()


def test_restore_failed_and_aborted_jobs(himena_ui: MainWindow, project: Path):
    # job_pipeline.star is still "Running". The status is restored from the files.
    mcor_dir = JobDirectory(project / MOTIONCORR_JOB)
    for filename, status in [
        (FileNames.EXIT_FAILURE, "Failed"),
        (FileNames.EXIT_ABORTED, "Aborted"),
    ]:
        mcor_dir.path.joinpath(filename).touch()
        with choose_one_dialog_response(himena_ui, True):
            _impl.trash_job(himena_ui, mcor_dir)
        assert statuses(read_pipeline(project)) == {IMPORT_JOB: "Succeeded"}
        _impl.restore_trashed_jobs(project, ["MotionCorr/job002"])
        assert _status(project, MOTIONCORR_JOB) == status
        mcor_dir.path.joinpath(filename).unlink()


def test_continue_job(himena_ui: MainWindow, project: Path, relion):
    relion.finish(MOTIONCORR_JOB)
    job_dir = JobDirectory(project / MOTIONCORR_JOB)

    # continue from the scheduler
    scheduler = MotionCorrOwnContinue._show_scheduler_widget_for_continue(
        himena_ui, {_job_class._JOB_DIR_ARGS_NAME: job_dir, "nr_threads": 3}
    )
    assert scheduler.get_parameters()["nr_threads"] == 3
    MotionCorrOwnContinue(job_dir).continue_job(
        **default_kwargs(MotionCorrOwnContinue, nr_threads=3)
    )
    job_star = JobStarModel.validate_file(job_dir.job_star())
    assert job_star.job.job_is_continue == 1
    assert job_dir.get_job_param("nr_threads") == "3"
    assert job_dir.get_job_param("input_star_mics") == MOVIES_STAR
    pipeline = read_pipeline(project)
    assert statuses(pipeline)[MOTIONCORR_JOB] == "Scheduled"
    assert input_edges(pipeline) == [(MOVIES_STAR, MOTIONCORR_JOB)]
    check_scheduled_jobs(project)
    assert relion.run_calls == [IMPORT_JOB, MOTIONCORR_JOB, MOTIONCORR_JOB]
    relion.finish(MOTIONCORR_JOB)

    # the job directory must be given
    with pytest.raises(RuntimeError):
        MotionCorrOwnContinue._show_scheduler_widget_for_continue(
            himena_ui, {_job_class._JOB_DIR_ARGS_NAME: "not a job directory"}
        )

    # continue immediately with the same parameters
    job_dir.path.joinpath(FileNames.ABORT_NOW).touch()
    execution = _job_class.continue_job_now(job_dir)
    assert execution.job_directory.path == job_dir.path
    assert relion.run_calls[-1] == MOTIONCORR_JOB
    assert _status(project, MOTIONCORR_JOB) == "Running"
    assert not job_dir.path.joinpath(FileNames.EXIT_SUCCESS).exists()
    assert not job_dir.path.joinpath(FileNames.ABORT_NOW).exists()
    assert JobStarModel.validate_file(job_dir.job_star()).job.job_is_continue == 1


def test_missing_input_file(himena_ui: MainWindow, in_project: Path, relion):
    start_new_project(himena_ui, in_project)
    _create_import_job(in_project)
    # MotionCorr uses a file that Import does not write
    missing = "Import/job001/not_found.star"
    assert _create_motioncorr_job(in_project, missing) is None
    mcor_path = in_project / MOTIONCORR_JOB
    assert is_all_inputs_ready(mcor_path) is ReadyState.NOT_READY
    check_scheduled_jobs(in_project)
    relion.finish(IMPORT_JOB)
    assert is_all_inputs_ready(mcor_path) is ReadyState.FILE_NOT_FOUND

    # the pipeline cannot be updated while RELION is editing it
    lock_dir = in_project / ".relion_lock"
    lock_dir.mkdir()
    check_scheduled_jobs(in_project)
    assert _status(in_project, MOTIONCORR_JOB) == "Scheduled"
    lock_dir.rmdir()

    check_scheduled_jobs(in_project)
    assert relion.run_calls == [IMPORT_JOB]
    assert _status(in_project, MOTIONCORR_JOB) == "Failed"
    assert mcor_path.joinpath(FileNames.EXIT_FAILURE).exists()
    assert "input files are not found" in mcor_path.joinpath("run.err").read_text()

    # jobs without job_pipeline.star cannot be checked
    mcor_path.joinpath("job_pipeline.star").unlink()
    assert is_all_inputs_ready(mcor_path) is ReadyState.PIPELINE_NOT_FOUND


def test_jobs_are_not_run_while_relion_is_locked(
    himena_ui: MainWindow, in_project: Path, relion
):
    start_new_project(himena_ui, in_project)
    _create_import_job(in_project)
    lock_dir = in_project / ".relion_lock"
    lock_dir.mkdir()
    check_scheduled_jobs(in_project)
    assert relion.run_calls == []
    assert _status(in_project, IMPORT_JOB) == "Scheduled"
    lock_dir.rmdir()
    check_scheduled_jobs(in_project)
    assert relion.run_calls == [IMPORT_JOB]


def test_run_scheduled_job_now(
    himena_ui: MainWindow, in_project: Path, relion, monkeypatch
):
    from himena_relion.pipeline.widgets import QRelionPipelineFlowChart

    start_new_project(himena_ui, in_project)
    _create_import_job(in_project)
    _create_motioncorr_job(in_project)
    check_scheduled_jobs(in_project)
    # Import is still running
    assert relion.run_calls == [IMPORT_JOB]
    assert _status(in_project, MOTIONCORR_JOB) == "Scheduled"

    for dock in himena_ui.dock_widgets:
        if isinstance(flowchart := dock.widget, QRelionPipelineFlowChart):
            break
    else:
        raise AssertionError("flowchart not found")
    started = []
    monkeypatch.setattr(_job_class, "run_watcher_new_process", started.append)
    run_now_path = in_project / MOTIONCORR_JOB / FileNames.RUN_NOW

    # the job is not run by the main window, but by the watcher
    flowchart._run_this_scheduled_job_now(Path(MOTIONCORR_JOB))
    assert run_now_path.exists()
    assert started == [in_project]
    assert relion.run_calls == [IMPORT_JOB]

    # not run while RELION is editing the pipeline; the request is kept
    lock_dir = in_project / ".relion_lock"
    lock_dir.mkdir()
    watcher_lock = in_project / pipeline_watcher._WATCHER_FILE_NAME
    watcher_lock.touch()
    check_scheduled_jobs(in_project)
    assert relion.run_calls == [IMPORT_JOB]
    assert run_now_path.exists()
    assert watcher_lock.exists()  # the watcher does not exit
    watcher_lock.unlink()
    lock_dir.rmdir()

    check_scheduled_jobs(in_project)
    assert relion.run_calls == [IMPORT_JOB, MOTIONCORR_JOB]
    assert not run_now_path.exists()

    # the request is not left if the pipeline could not be updated
    relion.finish(MOTIONCORR_JOB)
    lock_dir.mkdir()
    with pytest.raises(Exception):
        flowchart._run_this_scheduled_job_now(Path(MOTIONCORR_JOB))
    assert not run_now_path.exists()
    lock_dir.rmdir()


def test_execute_missing_job(in_project: Path):
    with pytest.raises(FileNotFoundError):
        pipeline_watcher.execute_job("Import/job001/", cwd=in_project)
    assert pipeline_watcher.execute_job("Import/job001/", True, cwd=in_project) is None
    log = in_project / pipeline_watcher._WATCHER_LOG_FILE_NAME
    assert "Error executing RELION job Import/job001/" in log.read_text()


def test_watcher_loop(himena_ui: MainWindow, in_project: Path, relion, monkeypatch):
    """Run the watcher loop with the file changes that RELION would make."""
    start_new_project(himena_ui, in_project)
    _create_import_job(in_project)
    _create_motioncorr_job(in_project)
    path = str(in_project / DEFAULT_PIPELINE_STAR)
    lock = in_project / pipeline_watcher._WATCHER_FILE_NAME
    seen: list[tuple[str, bool]] = []

    def _watch(_path):
        assert Path(_path) == Path(path)
        seen.append(("start", lock.exists()))
        assert relion.run_calls == [IMPORT_JOB]
        # Nothing changed. The pipeline is checked again after many timeouts.
        for _ in range(30):
            yield set()
        assert relion.run_calls == [IMPORT_JOB]
        # the file cannot be read while RELION is replacing it
        moved = Path(path).rename(Path(path).with_suffix(".tmp"))
        yield {(pipeline_watcher.Change.modified, path)}
        moved.rename(path)
        # Import finished
        relion.finish(IMPORT_JOB)
        yield {(pipeline_watcher.Change.modified, path)}
        assert relion.run_calls == [IMPORT_JOB, MOTIONCORR_JOB]
        # MotionCorr finished: nothing to run, and the lock is removed
        relion.finish(MOTIONCORR_JOB)
        yield {(pipeline_watcher.Change.modified, path)}
        seen.append(("end", lock.exists()))
        yield {(pipeline_watcher.Change.modified, path)}
        raise AssertionError("The watcher must exit when the lock is removed")

    monkeypatch.setattr(pipeline_watcher, "watch", _watch)
    monkeypatch.setattr(pipeline_watcher.time, "sleep", lambda *_: None)
    pipeline_watcher.run_watcher(in_project)
    assert seen == [("start", True), ("end", False)]
    assert statuses(read_pipeline(in_project)) == {
        IMPORT_JOB: "Succeeded",
        MOTIONCORR_JOB: "Succeeded",
    }
    log = in_project.joinpath(pipeline_watcher._WATCHER_LOG_FILE_NAME).read_text()
    assert "Start new pipeline watcher" in log
    assert "Lock file removed, exiting" in log
    assert "End pipeline watcher" in log


def test_watcher_without_project(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        pipeline_watcher.run_watcher(tmp_path)


def test_watcher_already_running(in_project: Path, monkeypatch):
    in_project.joinpath(DEFAULT_PIPELINE_STAR).write_text(
        "\n\ndata_pipeline_general\n\n_rlnPipeLineJobCounter       1\n"
    )

    def _locked(self):
        raise pipeline_watcher.WatcherAlreadyRunningError("locked")

    monkeypatch.setattr(pipeline_watcher.RelionPipelineWatcher, "_acquire_lock", _locked)
    pipeline_watcher.run_watcher(in_project, locked_ok=True)
    with pytest.raises(pipeline_watcher.WatcherAlreadyRunningError):
        pipeline_watcher.run_watcher(in_project, locked_ok=False)


def test_main_runs_watcher(in_project: Path, monkeypatch):
    from himena_relion import __main__ as main_module

    calls = []
    monkeypatch.setattr(
        main_module, "run_watcher", lambda **kwargs: calls.append(kwargs)
    )
    monkeypatch.setattr(main_module, "run_function", lambda: calls.append("function"))
    for argv in [
        ["watch"],
        ["watch", "project"],
        ["watch", "project", "--lock-ok"],
        ["some.module:Job", "--o", "External/job001/"],
    ]:
        monkeypatch.setattr(main_module.sys, "argv", ["himena-relion", *argv])
        main_module.main()
    assert calls == [
        {"relion_dir": in_project, "locked_ok": False},
        {"relion_dir": Path("project"), "locked_ok": False},
        {"relion_dir": Path("project"), "locked_ok": True},
        "function",
    ]


def test_scheduling_with_outdated_watcher(in_project: Path, monkeypatch):
    """The watcher is restarted even if scheduling failed after stopping the old one."""
    started = []
    monkeypatch.setattr(_job_class, "run_watcher_new_process", started.append)
    monkeypatch.setattr(_job_class, "stop_outdated_watcher", lambda _: True)
    with pytest.raises(ValueError):
        with _job_class._scheduling_jobs(in_project):
            raise ValueError("failed to schedule")
    assert started == [in_project]

    # nothing was stopped: the watcher is started only on success
    monkeypatch.setattr(_job_class, "stop_outdated_watcher", lambda _: False)
    with pytest.raises(ValueError):
        with _job_class._scheduling_jobs(in_project):
            raise ValueError("failed to schedule")
    assert started == [in_project]

    # the old watcher could not be stopped: warned, and the jobs are still scheduled
    def _cannot_stop(_):
        raise pipeline_watcher.OutdatedWatcherError("cannot stop")

    monkeypatch.setattr(_job_class, "stop_outdated_watcher", _cannot_stop)
    with pytest.warns(RuntimeWarning, match="cannot stop"):
        with _job_class._scheduling_jobs(in_project):
            pass
    assert started == [in_project, in_project]


def test_add_job_from_star_command(in_project: Path, monkeypatch):
    """The command line of `relion_pipeliner --addJobFromStar`."""
    job_star = in_project / "job.star"
    job_star.write_text("data_job\n")
    calls = []

    def _run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, returncode, "", "something wrong")

    monkeypatch.setattr(_job_class.subprocess, "run", _run)
    monkeypatch.setattr(
        _job_class._configs, "get_relion_pipeliner_args", lambda *_, **__: ["pipeliner"]
    )
    returncode = 0
    _job_class._run_relion_pipeliner_add_job_from_star(job_star, in_project)
    _job_class._run_relion_pipeliner_add_job_from_star(
        job_star, in_project, alias="my-alias"
    )
    assert calls == [
        ["pipeliner", "--addJobFromStar", str(job_star)],
        ["pipeliner", "--addJobFromStar", str(job_star), "--setJobAlias", "my-alias"],
    ]
    returncode = 1
    with pytest.raises(RuntimeError, match="something wrong"):
        _job_class._run_relion_pipeliner_add_job_from_star(job_star, in_project)


def test_new_job_command(himena_ui: MainWindow, in_project: Path):
    with choose_one_dialog_response(himena_ui, MotionCorrOwnJob.command_id()):
        _impl.new_job(himena_ui)
    scheduler = _job_class.scheduler_widget(himena_ui)
    assert "input_star_mics" in scheduler.get_parameters()
    assert MotionCorrOwnJob.command_id() in [
        cmd.command_id for cmd in _job_class.RelionJob.__relion_job_commands__
    ]
    with choose_one_dialog_response(himena_ui, None):
        _impl.new_job(himena_ui, ignore_cancelled=True)
        with pytest.raises(Cancelled):
            _impl.new_job(himena_ui)
    # the same scheduler is used
    assert _job_class.scheduler_widget(himena_ui) is scheduler


def test_scheduler_widget(himena_ui: MainWindow, in_project: Path, relion):
    start_new_project(himena_ui, in_project)

    # schedule a new job
    himena_ui.exec_action(ImportMoviesJob.command_id())
    scheduler = _job_class.scheduler_widget(himena_ui)
    scheduler.update_by_job(ImportMoviesJob, cwd=in_project)
    assert scheduler.cwd == in_project
    assert scheduler._exec_btn.text() == "Create Job"
    params = scheduler.get_parameters()
    params["fn_in_raw"] = "Movies/*.eer"
    scheduler._job_param_widget.set_parameters(params)
    scheduler.preview_job_star()
    preview = himena_ui.current_model.value
    assert "relion.import.movies" in preview and "Movies/*.eer" in preview
    scheduler.copy_job_star()
    assert himena_ui.clipboard.text == preview

    # nothing is done while RELION is editing the pipeline
    lock_dir = in_project / ".relion_lock"
    lock_dir.mkdir()
    scheduler._exec_btn.click()
    assert not in_project.joinpath(IMPORT_JOB).exists()
    lock_dir.rmdir()

    scheduler._exec_btn.click()
    assert statuses(read_pipeline(in_project)) == {IMPORT_JOB: "Scheduled"}
    import_dir = himena_ui.current_model.value
    assert isinstance(import_dir, JobDirectory)
    assert import_dir.job_normal_id() == IMPORT_JOB
    assert import_dir.get_job_param("fn_in_raw") == "Movies/*.eer"
    # the scheduler is cleared
    with pytest.raises(RuntimeError, match="No job class selected"):
        scheduler.get_parameters()

    # paste the parameters from job.star in the clipboard
    himena_ui.exec_action(ImportMoviesJob.command_id())
    assert scheduler.get_parameters()["fn_in_raw"] != "Movies/*.eer"
    scheduler.paste_from_job_star()
    assert scheduler.get_parameters()["fn_in_raw"] == "Movies/*.eer"
    # job.star of another job type is ignored
    himena_ui.exec_action(MotionCorrOwnJob.command_id())
    before = scheduler.get_parameters()
    scheduler.paste_from_job_star()
    assert scheduler.get_parameters() == before

    # continue a job
    check_scheduled_jobs(in_project)
    relion.finish(IMPORT_JOB)
    _create_motioncorr_job(in_project)
    check_scheduled_jobs(in_project)
    relion.finish(MOTIONCORR_JOB)
    mcor_dir = JobDirectory(in_project / MOTIONCORR_JOB)
    MotionCorrOwnContinue._show_scheduler_widget_for_continue(
        himena_ui, {_job_class._JOB_DIR_ARGS_NAME: mcor_dir, "nr_threads": 5}
    )
    assert scheduler._exec_btn.text() == "Continue Job"
    scheduler.preview_job_star()
    preview = himena_ui.current_model.value
    assert "relion.motioncorr.own" in preview and MOVIES_STAR in preview
    assert JobStarModel.validate_text(preview).job.job_is_continue == 1
    lock_dir.mkdir()
    scheduler._exec_btn.click()
    assert _status(in_project, MOTIONCORR_JOB) == "Succeeded"
    lock_dir.rmdir()
    scheduler._exec_btn.click()
    assert _status(in_project, MOTIONCORR_JOB) == "Scheduled"
    assert mcor_dir.get_job_param("nr_threads") == "5"

    # overwrite a job
    _impl.overwrite_relion_job(himena_ui, mcor_dir)
    assert scheduler._exec_btn.text() == "Overwrite"
    mcor_dir.path.joinpath("run.out").write_text("old log")
    lock_dir.mkdir()
    scheduler._exec_btn.click()
    lock_dir.rmdir()
    scheduler._exec_btn.click()
    assert not mcor_dir.path.joinpath("run.out").exists()
    assert JobStarModel.validate_file(mcor_dir.job_star()).job.job_is_continue == 0
    assert _status(in_project, MOTIONCORR_JOB) == "Scheduled"
