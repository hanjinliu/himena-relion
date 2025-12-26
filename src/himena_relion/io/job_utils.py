from __future__ import annotations

from typing import TYPE_CHECKING
from himena import MainWindow, WidgetDataModel
from himena.exceptions import Cancelled
from himena.plugins import register_function
from himena_relion.consts import Type, MenuId, RelionJobState, FileNames

if TYPE_CHECKING:
    from himena_relion._job_dir import JobDirectory


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Open job.star as text",
    command_id="himena-relion:open-job-star",
    group="00-open-file",
)
def open_relion_job_star(ui: MainWindow, model: WidgetDataModel) -> WidgetDataModel:
    job_dir = assert_job(model)
    job_star_path = job_dir.job_star()
    ui.read_file(job_star_path, plugin="himena_builtins.io.read_as_text_anyway")


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Open job_pipeline.star as text",
    command_id="himena-relion:open-job-pipeline-star",
    group="00-open-file",
)
def open_relion_job_pipeline_star(
    ui: MainWindow, model: WidgetDataModel
) -> WidgetDataModel:
    job_dir = assert_job(model)
    job_star_path = job_dir.job_pipeline()
    ui.read_file(job_star_path, plugin="himena_builtins.io.read_as_text_anyway")


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Mark job as finished",
    command_id="himena-relion:mark-finished",
    group="03-job-mark",
)
def mark_as_finished(model: WidgetDataModel):
    """Mark this job as 'finished'"""
    job_dir = assert_job(model)
    job_dir.path.joinpath(FileNames.EXIT_SUCCESS).touch()


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Mark job as failed",
    command_id="himena-relion:mark-failed",
    group="03-job-mark",
)
def mark_as_failed(model: WidgetDataModel):
    """Mark this job as 'failed'"""
    job_dir = assert_job(model)
    job_dir.path.joinpath(FileNames.EXIT_FAILURE).touch()


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Abort job",
    command_id="himena-relion:abort-job",
    group="07-job-operation",
)
def abort_relion_job(ui: MainWindow, model: WidgetDataModel):
    """Abort this RELION job."""
    job_dir = assert_job(model)
    if job_dir.state() == RelionJobState.EXIT_SUCCESS:
        raise RuntimeError("Cannot abort a finished job.")
    ans = ui.exec_choose_one_dialog(
        title="Abort job?",
        message="Are you sure you want to abort this job?",
        choices=["Yes, abort", "Cancel"],
    )
    if ans == "Yes, abort":
        job_dir.path.joinpath(FileNames.ABORT_NOW).touch()


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Edit job",
    command_id="himena-relion:edit-job",
    group="07-job-operation",
)
def edit_relion_job(ui: MainWindow, model: WidgetDataModel):
    """Edit this RELION job's parameters and overwrite."""
    job_dir = assert_job(model)
    job_cls = job_dir._to_job_class()
    if job_cls is None:
        raise RuntimeError("Cannot determine job class.")

    scheduler = job_cls._show_scheduler_widget(ui, {})
    scheduler.set_edit_mode(job_dir)
    scheduler.set_parameters(job_dir.get_job_params_as_dict())


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Clone job",
    command_id="himena-relion:clone-job",
    group="07-job-operation",
)
def clone_relion_job(ui: MainWindow, model: WidgetDataModel):
    """Clone this RELION job.

    This will not immediately make a copy of the job directory, so it is different from
    the clone operation in cryoSPARC. Parameters from this job will be copied to the
    job runner widget to facilitate creating a new job with the same parameters.
    """
    job_dir = assert_job(model)
    job_cls = job_dir._to_job_class()
    if job_cls is None:
        raise RuntimeError("Cannot determine job class.")
    scheduler = job_cls._show_scheduler_widget(ui, {})
    scheduler.update_by_job(job_cls)
    scheduler.set_parameters(job_dir.get_job_params_as_dict())
    scheduler.set_schedule_mode()


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Reopen this job",
    command_id="himena-relion:reopen-job",
    group="07-job-operation",
)
def reopen_relion_job(model: WidgetDataModel) -> WidgetDataModel:
    """Reopen this RELION job.

    If some error occurred during reading the job directory and the widget stop working,
    this function can be used to initialize the widget again.
    """
    return model.with_value(model.value, update_inplace=True).use_tab()


@register_function(
    menus=[MenuId.RELION_UTILS],
    title="Start New RELION Project",
    command_id="himena-relion:start-new-project",
    group="11-others",
)
def start_new_project(ui: MainWindow):
    """Start a new RELION project under the selected directory."""
    text = "\n\ndata_pipeline_general\n\n_rlnPipeLineJobCounter       1\n"
    if path_dir := ui.exec_file_dialog("d", caption="Select Project Directory"):
        path = path_dir / "default_pipeline.star"
        if path.exists():
            ui.show_notification(
                "Selected directory is already a RELION project. Opening existing file."
            )
        else:
            path.write_text(text)
        ui.read_file(path)
        return
    raise Cancelled


def assert_job(model: WidgetDataModel) -> JobDirectory:
    from himena_relion._job_dir import JobDirectory

    value = model.value
    if not isinstance(value, JobDirectory):
        raise TypeError(f"Expected JobDirectory object, got {type(value)}")
    return value
