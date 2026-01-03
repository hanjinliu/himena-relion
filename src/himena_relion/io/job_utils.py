from __future__ import annotations

import logging
from pathlib import Path
import subprocess
from typing import TYPE_CHECKING
from himena import MainWindow, WidgetDataModel
from himena.exceptions import Cancelled
from himena.plugins import register_function
from himena_relion.consts import Type, MenuId, RelionJobState, FileNames
from himena_relion._utils import normalize_job_id, update_default_pipeline
from himena_relion.schemas._pipeline import RelionPipelineModel

if TYPE_CHECKING:
    from himena_relion._job_dir import JobDirectory

_LOGGER = logging.getLogger(__name__)


@register_function(
    menus=[MenuId.RELION_UTILS, "/model_menu/open"],
    types=[Type.RELION_JOB],
    title="Open job.star as text",
    command_id="himena-relion:open-job-star",
)
def open_relion_job_star(ui: MainWindow, model: WidgetDataModel):
    """Openthe job.star file of this RELION job as text."""
    job_dir = assert_job(model)
    job_star_path = job_dir.job_star()
    ui.read_file(
        job_star_path,
        plugin="himena_builtins.io.read_as_text_anyway",
        append_history=False,
    )


@register_function(
    menus=[MenuId.RELION_UTILS, "/model_menu/open"],
    types=[Type.RELION_JOB],
    title="Open job_pipeline.star as text",
    command_id="himena-relion:open-job-pipeline-star",
)
def open_relion_job_pipeline_star(ui: MainWindow, model: WidgetDataModel):
    """Open the job_pipeline.star file of this RELION job as text."""
    job_dir = assert_job(model)
    job_star_path = job_dir.job_pipeline()
    ui.read_file(
        job_star_path,
        plugin="himena_builtins.io.read_as_text_anyway",
        append_history=False,
    )


@register_function(
    menus=[MenuId.RELION_UTILS, "/model_menu/cleanup"],
    types=[Type.RELION_JOB],
    title="Gentle clean",
    command_id="himena-relion:gentle-clean",
)
def gentle_clean_relion_job(ui: MainWindow, model: WidgetDataModel):
    """Perform a gentle clean of this RELION job."""
    job_dir = assert_job(model)
    job_num = int(job_dir.job_number)
    # Work like this:
    # $ relion_pipeliner --gentle_clean 5
    subprocess.run(
        ["relion_pipeliner", "--gentle_clean", str(job_num)],
        check=True,
        cwd=job_dir.relion_project_dir,
    )
    ui.show_notification(f"Gentle cleaned job {job_dir.job_normal_id()}.")


@register_function(
    menus=[MenuId.RELION_UTILS, "/model_menu/cleanup"],
    types=[Type.RELION_JOB],
    title="Harsh clean",
    command_id="himena-relion:harsh-clean",
)
def harsh_clean_relion_job(ui: MainWindow, model: WidgetDataModel):
    """Perform a harsh clean of this RELION job."""
    job_dir = assert_job(model)
    job_num = int(job_dir.job_number)
    # Work like this:
    # $ relion_pipeliner --harsh_clean 5
    subprocess.run(
        ["relion_pipeliner", "--harsh_clean", str(job_num)],
        check=True,
        cwd=job_dir.relion_project_dir,
    )
    ui.show_notification(f"Harsh cleaned job {job_dir.job_normal_id()}.")


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
    title="Overwrite ...",
    command_id="himena-relion:overwrite-job",
    group="07-job-operation",
)
def overwrite_relion_job(ui: MainWindow, model: WidgetDataModel):
    """Overwrite this RELION job's parameters and execute again."""
    job_dir = assert_job(model)
    job_cls = job_dir._to_job_class()
    if job_cls is None:
        raise RuntimeError("Cannot determine job class.")

    scheduler = job_cls._show_scheduler_widget(ui, {}, cwd=job_dir.relion_project_dir)
    scheduler.set_edit_mode(job_dir)
    scheduler.set_parameters(job_dir.get_job_params_as_dict())


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
    job_cls = job_dir._to_job_class()
    if job_cls is None:
        raise RuntimeError("Cannot determine job class.")
    scheduler = job_cls._show_scheduler_widget(ui, {}, cwd=job_dir.relion_project_dir)
    scheduler.update_by_job(job_cls, cwd=job_dir.relion_project_dir)
    scheduler.set_parameters(job_dir.get_job_params_as_dict())
    scheduler.set_schedule_mode()


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Set Alias ...",
    command_id="himena-relion:set-job-alias",
    group="07-job-operation",
)
def set_job_alias(ui: MainWindow, model: WidgetDataModel):
    """Set alias for this RELION job."""
    job_dir = assert_job(model)
    res = ui.exec_user_input_dialog({"alias": str}, title="Set Job Alias")
    if res is None:
        raise Cancelled
    alias = str(res["alias"]).strip()
    if alias == "" or alias.startswith("job"):
        raise ValueError("Alias cannot be empty or start with 'job'.")

    # Check if alias is a valid folder name
    invalid_chars = '*?()/"\\|#<>&%{}$'
    if any(char in alias for char in invalid_chars):
        raise ValueError(f"Alias contains invalid characters. Avoid: {invalid_chars}")
    if set(alias) == {"."}:
        raise ValueError("Alias cannot be '.' or '..'")
    if (job_dir.path.parent / alias).exists():
        raise FileExistsError(f"Alias '{alias}' already exists.")

    new_path = job_dir.path.parent / alias
    for other_job in job_dir.path.parent.iterdir():
        if other_job.is_symlink() and other_job.resolve() == job_dir.path:
            # this is the old alias for this job
            other_job.rename(new_path)
            break
    else:
        # no existing alias, create a new one
        new_path.symlink_to(job_dir.path, target_is_directory=True)
    update_default_pipeline(
        job_dir.relion_project_dir / "default_pipeline.star",
        job_dir.path.relative_to(job_dir.relion_project_dir),
        alias=normalize_job_id(new_path),
    )


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Trash",
    command_id="himena-relion:trash-job",
    group="07-job-operation",
)
def trash_job(ui: MainWindow, model: WidgetDataModel):
    """Move this RELION job to trash."""
    from himena_relion._job_dir import JobDirectory

    job_dir = assert_job(model)
    rln_dir = job_dir.relion_project_dir
    trash_dir = rln_dir.joinpath("Trash")
    with rln_dir.joinpath("default_pipeline.star").open("r+") as f:
        pipeline = RelionPipelineModel.validate_text(f.read())
        input_indices_to_remove: list[int] = []
        output_indices_to_remove: list[int] = []
        # to_trash is all the relative paths to be moved to trash
        to_trash = [job_dir.path.relative_to(rln_dir)]
        for ith, (from_, to_) in enumerate(
            zip(pipeline.input_edges.from_node, pipeline.input_edges.process)
        ):
            job_spec = Path(to_)
            if Path(from_).parent in to_trash or job_spec in to_trash:
                if (
                    not job_spec.is_absolute()
                    and len(job_spec.parts) == 2
                    and job_spec not in to_trash[::-1]  # faster to search backwards
                ):
                    to_trash.append(job_spec)
                input_indices_to_remove.append(ith)
        for ith, from_ in enumerate(pipeline.output_edges.process):
            if Path(from_) in to_trash:
                output_indices_to_remove.append(ith)
        # prepare HTML message
        message_lines = ["<p>Following jobs would be moved to trash:</p><ul>"]
        for p in to_trash:
            message_lines.append(f"<li>{p}</li>")
            if len(message_lines) >= 16:
                message_lines.append("<li>...</li>")  # truncate long list
                break
        message_lines.append("</ul>")
        # ask user
        if (
            ui.exec_choose_one_dialog(
                title="Trash job?",
                message="".join(message_lines),
                choices=["Yes, move to trash", "Cancel"],
            )
            != "Yes, move to trash"
        ):
            raise Cancelled

        # determine other fields to remove
        process_name_to_remove: list[int] = []
        for ith, name in enumerate(pipeline.processes.process_name):
            if Path(name) in to_trash:
                process_name_to_remove.append(ith)

        process_nodes_to_remove: list[int] = []
        for ith, name in enumerate(pipeline.nodes.name):
            if Path(name).parent in to_trash:
                process_nodes_to_remove.append(ith)

        pipeline.processes = pipeline.processes.dataframe.drop(
            index=process_name_to_remove
        )
        pipeline.nodes = pipeline.nodes.dataframe.drop(index=process_nodes_to_remove)
        pipeline.input_edges = pipeline.input_edges.dataframe.drop(
            index=input_indices_to_remove
        )
        pipeline.output_edges = pipeline.output_edges.dataframe.drop(
            index=output_indices_to_remove
        )

        # close all the tabs with trashed jobs
        try:
            tabs_to_close: list[int] = []
            for i_tab, tab in ui.tabs.enumerate():
                if (
                    len(tab) > 0
                    and isinstance(_job_dir := tab[0].value, JobDirectory)
                    and _job_dir.path.relative_to(rln_dir) in to_trash
                ):
                    tabs_to_close.append(i_tab)
            for i_tab in reversed(tabs_to_close):
                del ui.tabs[i_tab]
        except Exception:
            _LOGGER.warning("Failed to close tabs for trashed jobs.", exc_info=True)

        f.seek(0)
        f.write(pipeline.to_string())
        trash_dir.mkdir(exist_ok=True)
        for p in to_trash:
            src = rln_dir / p
            dest = trash_dir / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dest)


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
        return
    raise Cancelled


@register_function(
    menus=[MenuId.RELION_UTILS],
    title="Undo Trash RELION jobs",
    command_id="himena-relion:undo-trash-jobs",
)
def undo_trash_jobs(ui: MainWindow):
    raise NotImplementedError


def assert_job(model: WidgetDataModel) -> JobDirectory:
    from himena_relion._job_dir import JobDirectory

    value = model.value
    if not isinstance(value, JobDirectory):
        raise TypeError(f"Expected JobDirectory object, got {type(value)}")
    return value
