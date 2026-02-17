from __future__ import annotations

import logging
from pathlib import Path
import subprocess
import shutil
from typing import TYPE_CHECKING, Annotated
from himena import MainWindow
from himena.exceptions import Cancelled
from himena_relion.consts import RelionJobState, FileNames
from himena_relion._utils import normalize_job_id, update_default_pipeline
from himena_relion.schemas._pipeline import RelionPipelineModel

if TYPE_CHECKING:
    from himena_relion._job_dir import JobDirectory
    import pandas as pd

_LOGGER = logging.getLogger(__name__)


def open_relion_job_star(ui: MainWindow, job_dir: JobDirectory):
    """Openthe job.star file of this RELION job as text."""
    job_star_path = job_dir.job_star()
    ui.read_file(
        job_star_path,
        plugin="himena_builtins.io.read_as_text_anyway",
        append_history=False,
    )


def open_relion_job_pipeline_star(ui: MainWindow, job_dir: JobDirectory):
    """Open the job_pipeline.star file of this RELION job as text."""
    job_star_path = job_dir.job_pipeline()
    ui.read_file(
        job_star_path,
        plugin="himena_builtins.io.read_as_text_anyway",
        append_history=False,
    )


def gentle_clean_relion_job(ui: MainWindow, job_dir: JobDirectory):
    """Perform a gentle clean of this RELION job."""
    job_num = int(job_dir.job_number)
    # Work like this:
    # $ relion_pipeliner --gentle_clean 5
    subprocess.run(
        ["relion_pipeliner", "--gentle_clean", str(job_num)],
        check=True,
        cwd=job_dir.relion_project_dir,
    )
    ui.show_notification(f"Gentle cleaned job {job_dir.job_normal_id()}.")


def harsh_clean_relion_job(ui: MainWindow, job_dir: JobDirectory):
    """Perform a harsh clean of this RELION job."""
    job_num = int(job_dir.job_number)
    # Work like this:
    # $ relion_pipeliner --harsh_clean 5
    subprocess.run(
        ["relion_pipeliner", "--harsh_clean", str(job_num)],
        check=True,
        cwd=job_dir.relion_project_dir,
    )
    ui.show_notification(f"Harsh cleaned job {job_dir.job_normal_id()}.")


def mark_as_finished(job_dir: JobDirectory):
    """Mark this job as 'finished'"""
    job_dir.path.joinpath(FileNames.EXIT_SUCCESS).touch()


def mark_as_failed(job_dir: JobDirectory):
    """Mark this job as 'failed'"""
    job_dir.path.joinpath(FileNames.EXIT_FAILURE).touch()


def abort_relion_job(ui: MainWindow, job_dir: JobDirectory):
    """Abort this RELION job."""
    if job_dir.state() == RelionJobState.EXIT_SUCCESS:
        raise RuntimeError("Cannot abort a finished job.")
    ans = ui.exec_choose_one_dialog(
        title="Abort job?",
        message="Are you sure you want to abort this job?",
        choices=["Yes, abort", "Cancel"],
    )
    if ans == "Yes, abort":
        job_dir.path.joinpath(FileNames.ABORT_NOW).touch()


def overwrite_relion_job(ui: MainWindow, job_dir: JobDirectory):
    """Overwrite this RELION job's parameters and execute again."""
    job_cls = job_dir._to_job_class()
    if job_cls is None:
        raise RuntimeError("Cannot determine job class.")

    scheduler = job_cls._show_scheduler_widget(ui, {}, cwd=job_dir.relion_project_dir)
    scheduler.set_edit_mode(job_dir)
    scheduler.set_parameters(job_dir.get_job_params_as_dict())


def clone_relion_job(ui: MainWindow, job_dir: JobDirectory):
    """Clone this RELION job.

    This will not immediately make a copy of the job directory, so it is different from
    the clone operation in cryoSPARC. Parameters from this job will be copied to the
    job runner widget to facilitate creating a new job with the same parameters.
    """
    job_cls = job_dir._to_job_class()
    if job_cls is None:
        raise RuntimeError("Cannot determine job class.")
    scheduler = job_cls._show_scheduler_widget(ui, {}, cwd=job_dir.relion_project_dir)
    scheduler.update_by_job(job_cls, cwd=job_dir.relion_project_dir)
    scheduler.set_parameters(job_dir.get_job_params_as_dict())
    scheduler.set_schedule_mode()


def set_job_alias(ui: MainWindow, job_dir: JobDirectory):
    """Set alias for this RELION job."""
    from himena_relion._widgets._main import QRelionJobWidget

    default_pipeline_path = job_dir.relion_project_dir / "default_pipeline.star"
    if not default_pipeline_path.exists():
        raise FileNotFoundError("default_pipeline.star not found")
    pipeline = RelionPipelineModel.validate_file(default_pipeline_path)
    # look for current alias
    _matched = pipeline.processes.process_name == job_dir.job_normal_id()
    matched = pipeline.processes.alias[_matched]
    if len(matched) == 1:
        current_alias = matched.iloc[0]
        if current_alias == "None":
            current_alias = ""
    else:
        current_alias = ""
    res = ui.exec_user_input_dialog(
        {"alias": Annotated[str, {"value": current_alias}]}, title="Set Job Alias"
    )
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
        default_pipeline_path,
        job_dir.path.relative_to(job_dir.relion_project_dir),
        alias=normalize_job_id(new_path),
    )
    # update the job widget title
    for window in ui.iter_windows():
        if (
            isinstance(widget := window.widget, QRelionJobWidget)
            and widget._job_dir.path == job_dir.path
        ):
            widget._state_widget.initialize(job_dir)


def trash_job(ui: MainWindow, job_dir: JobDirectory):
    """Move this RELION job to trash."""
    from himena_relion._job_dir import JobDirectory

    rln_dir = job_dir.relion_project_dir
    trash_dir = _trash_dir(rln_dir)
    # open the file to lock it.
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
        _yes = "Yes, move to trash"
        resp = ui.exec_choose_one_dialog(
            title="Trash job?",
            message="".join(message_lines),
            choices=[_yes, "Cancel"],
        )
        # ask user
        if resp != _yes:
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
            if dest.exists():
                _LOGGER.warning(f"Destination {dest} already exists. Overwriting.")
                _remove_dir_or_file(dest)
            src.rename(dest)
    rln_dir.joinpath("default_pipeline.star").touch()


def restore_trashed_jobs(relion_project_dir: Path, job_ids: list[str]):
    trash_dir = _trash_dir(relion_project_dir)
    all_jobs_to_undo: list[Path] = []
    for job_id in job_ids:
        job_path_in_trash = trash_dir / job_id
        if not job_path_in_trash.exists():
            _LOGGER.warning(f"Job {job_id} not found in trash.")
            continue
        all_jobs_to_undo.append(job_path_in_trash)

    # open the file to lock it.
    with relion_project_dir.joinpath("default_pipeline.star").open("r+") as f:
        pipeline = RelionPipelineModel.validate_text(f.read())
        all_processes = [pipeline.processes.dataframe]
        all_nodes = [pipeline.nodes.dataframe]
        all_input_edges = [pipeline.input_edges.dataframe]
        all_output_edges = [pipeline.output_edges.dataframe]
        for path_to_undo in all_jobs_to_undo:
            job_pipeline_star = path_to_undo / "job_pipeline.star"
            path_dest = relion_project_dir / path_to_undo.relative_to(trash_dir)
            if not job_pipeline_star.exists():
                _LOGGER.warning(f"{job_pipeline_star} not found. Skipping.")
                continue
            if path_dest.exists():
                _LOGGER.warning(f"Destination {path_dest} already exists. Skipping.")
                continue
            job_pipeline = RelionPipelineModel.validate_file(job_pipeline_star)
            df_proc = job_pipeline.processes.dataframe
            # job_pipeline.star is still in "Running" state, so we have to update it.
            sl = df_proc["rlnPipeLineProcessStatusLabel"] == "Running"
            if path_to_undo.joinpath(FileNames.EXIT_SUCCESS).exists():
                df_proc[sl] = ["Succeeded"] * sl.sum()
            elif path_to_undo.joinpath(FileNames.EXIT_FAILURE).exists():
                df_proc[sl] = ["Failed"] * sl.sum()
            elif path_to_undo.joinpath(FileNames.EXIT_ABORTED).exists():
                df_proc[sl] = ["Aborted"] * sl.sum()
            all_processes.append(job_pipeline.processes.dataframe)
            all_nodes.append(job_pipeline.nodes.dataframe)
            all_input_edges.append(job_pipeline.input_edges.dataframe)
            all_output_edges.append(job_pipeline.output_edges.dataframe)
            path_dest.parent.mkdir(parents=True, exist_ok=True)
            if path_dest.exists():
                _LOGGER.warning(f"Destination {path_dest} already exists. Overwriting.")
                _remove_dir_or_file(path_dest)
            path_to_undo.rename(path_dest)
        df_processes = _concat_and_reorder(all_processes, "rlnPipeLineProcessName")
        df_nodes = _concat_and_reorder(all_nodes, "rlnPipeLineNodeName")
        df_input_edges = _concat_and_reorder(all_input_edges, "rlnPipeLineEdgeFromNode")
        df_output_edges = _concat_and_reorder(
            all_output_edges, "rlnPipeLineEdgeProcess"
        )
        pipeline.processes = df_processes
        pipeline.nodes = df_nodes
        pipeline.input_edges = df_input_edges
        pipeline.output_edges = df_output_edges
        f.seek(0)
        f.write(pipeline.to_string())
    relion_project_dir.joinpath("default_pipeline.star").touch()


def _trash_dir(relion_job_dir: Path) -> Path:
    return relion_job_dir / "Trash"


def _remove_dir_or_file(dest: Path):
    if dest.is_dir():
        shutil.rmtree(dest)
    else:
        dest.unlink()


def _concat_and_reorder(dfs: list[pd.DataFrame], column_name: str):
    import pandas as pd

    df_processes = pd.concat(dfs, ignore_index=True)
    order = df_processes[column_name].apply(_try_get_job_name).argsort()
    return df_processes.iloc[order].reset_index(drop=True)


def _try_get_job_name(x: str) -> str:
    if "/" in x:
        return x.split("/")[1]
    return x
