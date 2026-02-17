from __future__ import annotations

from typing import TYPE_CHECKING
from himena import MainWindow, WidgetDataModel
from himena.exceptions import Cancelled
from himena.plugins import register_function
from himena_relion.consts import Type, MenuId, FileNames
from himena_relion.io import _impl
from himena_relion._utils import get_pipeline_widgets

if TYPE_CHECKING:
    from himena_relion._job_dir import JobDirectory


@register_function(
    menus=[MenuId.RELION_UTILS, "/model_menu/open"],
    types=[Type.RELION_JOB],
    title="Open job.star as text",
    command_id="himena-relion:open-job-star",
)
def open_relion_job_star(ui: MainWindow, model: WidgetDataModel):
    """Openthe job.star file of this RELION job as text."""
    job_dir = assert_job(model)
    return _impl.open_relion_job_star(ui, job_dir)


@register_function(
    menus=[MenuId.RELION_UTILS, "/model_menu/open"],
    types=[Type.RELION_JOB],
    title="Open job_pipeline.star as text",
    command_id="himena-relion:open-job-pipeline-star",
)
def open_relion_job_pipeline_star(ui: MainWindow, model: WidgetDataModel):
    """Open the job_pipeline.star file of this RELION job as text."""
    job_dir = assert_job(model)
    return _impl.open_relion_job_pipeline_star(ui, job_dir)


@register_function(
    menus=[MenuId.RELION_UTILS, "/model_menu/cleanup"],
    types=[Type.RELION_JOB],
    title="Gentle clean",
    command_id="himena-relion:gentle-clean",
)
def gentle_clean_relion_job(ui: MainWindow, model: WidgetDataModel):
    """Perform a gentle clean of this RELION job."""
    job_dir = assert_job(model)
    return _impl.gentle_clean_relion_job(ui, job_dir)


@register_function(
    menus=[MenuId.RELION_UTILS, "/model_menu/cleanup"],
    types=[Type.RELION_JOB],
    title="Harsh clean",
    command_id="himena-relion:harsh-clean",
)
def harsh_clean_relion_job(ui: MainWindow, model: WidgetDataModel):
    """Perform a harsh clean of this RELION job."""
    job_dir = assert_job(model)
    return _impl.harsh_clean_relion_job(ui, job_dir)


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Mark as finished",
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
    title="Mark as failed",
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
    title="Abort",
    command_id="himena-relion:abort-job",
    group="07-job-operation",
)
def abort_relion_job(ui: MainWindow, model: WidgetDataModel):
    """Abort this RELION job."""
    job_dir = assert_job(model)
    return _impl.abort_relion_job(ui, job_dir)


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Overwrite ...",
    command_id="himena-relion:overwrite-job",
    group="07-job-operation",
)
def overwrite_relion_job(ui: MainWindow, model: WidgetDataModel):
    """Overwrite this RELION job's parameters and execute again."""
    job_dir = assert_job(model)
    return _impl.overwrite_relion_job(ui, job_dir)


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Clone ...",
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
    return _impl.clone_relion_job(ui, job_dir)


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Set Alias ...",
    command_id="himena-relion:set-job-alias",  # do NOT change this ID, used elsewhere.
    group="07-job-operation",
)
def set_job_alias(ui: MainWindow, model: WidgetDataModel):
    """Set alias for this RELION job."""
    job_dir = assert_job(model)
    return _impl.set_job_alias(ui, job_dir)


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Trash RELION job",
    command_id="himena-relion:trash-job",
    group="07-job-operation",
)
def trash_job(ui: MainWindow, model: WidgetDataModel):
    """Move this RELION job to trash."""
    job_dir = assert_job(model)
    return _impl.trash_job(ui, job_dir)


@register_function(
    menus=[MenuId.RELION_UTILS],
    title="Restore Trashed RELION jobs",
    command_id="himena-relion:restore-trashed-jobs",
)
def restore_trashed_jobs(ui: MainWindow):
    if cur_widget := get_pipeline_widgets(ui):
        start_path = cur_widget._flow_chart._relion_project_dir
    else:
        start_path = None
    if res := ui.exec_file_dialog(
        "d",
        caption="Select RELION job directory to restore",
        start_path=start_path,
    ):
        parts = res.parts
        if len(parts) < 3 or parts[-3] != "Trash":
            raise ValueError("Selected directory is not a trashed job directory.")
        cur_relion_project_dir = res.parent.parent.parent
        job_id = f"{parts[-2]}/{parts[-1]}/"
        _impl.restore_trashed_jobs(cur_relion_project_dir, [job_id])
    else:
        raise Cancelled


@register_function(
    menus=[MenuId.RELION_UTILS],
    title="Start New RELION Project",
    command_id="himena-relion:start-new-project",
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
    else:
        raise Cancelled


def assert_job(model: WidgetDataModel) -> JobDirectory:
    from himena_relion._job_dir import JobDirectory

    value = model.value
    if not isinstance(value, JobDirectory):
        raise TypeError(f"Expected JobDirectory object, got {type(value)}")
    return value
