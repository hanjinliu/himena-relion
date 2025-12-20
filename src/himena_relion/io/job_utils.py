from __future__ import annotations

from typing import TYPE_CHECKING
from himena import MainWindow, WidgetDataModel, create_text_model
from himena.exceptions import Cancelled
from himena.plugins import register_function
from himena_relion.consts import Type, MenuId, RelionJobState, FileNames

if TYPE_CHECKING:
    from himena_relion._job import JobDirectory


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Open job.star as text",
    command_id="himena-relion:open-job-star",
    group="00-open-file",
)
def open_relion_job_star(model: WidgetDataModel) -> WidgetDataModel:
    job_dir = assert_job(model)
    job_star_path = job_dir.job_star()
    return create_text_model(
        job_star_path.read_text(),
        title=f"{job_dir.path.stem}/{job_star_path.name}",
        extension_default=".star",
    )


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Open job_pipeline.star as text",
    command_id="himena-relion:open-job-pipeline-star",
    group="00-open-file",
)
def open_relion_job_pipeline_star(model: WidgetDataModel) -> WidgetDataModel:
    job_dir = assert_job(model)
    job_star_path = job_dir.job_pipeline()
    return create_text_model(
        job_star_path.read_text(),
        title=f"{job_dir.path.stem}/{job_star_path.name}",
        extension_default=".star",
    )


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Mark job as finished",
    command_id="himena-relion:mark-finished",
    group="03-job-mark",
)
def mark_as_finished(model: WidgetDataModel):
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
    job_dir = assert_job(model)
    job_dir.path.joinpath(FileNames.EXIT_FAILURE).touch()


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Clone job",
    command_id="himena-relion:clone-job",
    group="07-job-operation",
)
def clone_relion_job(ui: MainWindow, model: WidgetDataModel):
    """Clone this RELION job."""
    job_dir = assert_job(model)
    job_cls = job_dir._to_job_class()
    if job_cls is None:
        raise RuntimeError("Cannot determine job class.")
    scheduler = job_cls._show_scheduler_widget(ui, {})
    scheduler.update_by_job(job_cls)
    scheduler.set_parameters(job_dir.get_job_params_as_dict())
    scheduler.set_edit_mode(job_dir)


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Abort job",
    command_id="himena-relion:abort-job",
    group="07-job-operation",
)
def abort_relion_job(ui: MainWindow, model: WidgetDataModel):
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
    job_dir = assert_job(model)
    job_cls = job_dir._to_job_class()
    if job_cls is None:
        raise RuntimeError("Cannot determine job class.")

    scheduler = job_cls._show_scheduler_widget(ui, {})
    scheduler.set_edit_mode(job_dir)
    scheduler.set_parameters(job_dir.get_job_params_as_dict())


@register_function(
    menus=[MenuId.RELION_UTILS],
    title="Initialize Project Directory",
    command_id="himena-relion:initialize-project-directory",
    group="11-others",
)
def initialize_project_directory(ui: MainWindow):
    text = "\n\ndata_pipeline_general\n\n_rlnPipeLineJobCounter       1\n"
    if path := ui.exec_file_dialog("d", caption="Select Project Directory"):
        path.write_text(text)
        return
    raise Cancelled


def assert_job(model: WidgetDataModel) -> JobDirectory:
    from himena_relion._job import JobDirectory

    value = model.value
    if not isinstance(value, JobDirectory):
        raise TypeError(f"Expected JobDirectory object, got {type(value)}")
    return value
