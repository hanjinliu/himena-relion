"""Useful startup function to use himena with RELION."""

from typing import TYPE_CHECKING

from pathlib import Path
import psutil
from himena_relion._job_dir import JobDirectory
from himena_relion._job_class import scheduler_widget
from himena_relion._utils import get_pipeline_widgets, read_or_show_job
from himena_relion.pipeline_watcher import (
    _WATCHER_FILE_NAME,
    read_pid_from_lock,
    get_user,
)
from himena_relion.pipeline import QRelionPipelineFlowChart
from himena_relion.pipeline._gui_state import HimenaRelionGuiState

if TYPE_CHECKING:
    from himena.widgets import MainWindow


def on_himena_startup(ui: "MainWindow"):
    """This function is called on himena startup."""
    cwd = Path.cwd()
    if (starpath := cwd.joinpath("default_pipeline.star")).exists():
        if get_pipeline_widgets(ui) is None:
            ui.read_file(starpath, plugin="himena_relion.io.read_relion_pipeline")
        scheduler = scheduler_widget(ui)
        scheduler.clear_content()
        ui.size = max(ui.size.width, 1260), ui.size.height

        # if pipeline-watcher lock exists, check if the process is actually running.
        if (lock := cwd.joinpath(_WATCHER_FILE_NAME)).exists():
            try:
                pid = read_pid_from_lock(lock)
            except Exception:
                lock.unlink()
                ui.show_notification(
                    f"Pipeline watcher lock file {_WATCHER_FILE_NAME} seems broken. "
                    "This lock is removed."
                )
                return
            try:
                process_name = psutil.Process(pid).name()
            except psutil.NoSuchProcess:
                process_name = ""
            else:
                if process_name != "himena-relion":
                    lock.unlink()
                    ui.show_notification(
                        f"Pipeline watcher lock file {_WATCHER_FILE_NAME} found, but "
                        "the process seems not running. This lock is removed."
                    )

        # try to recover the last opened jobs
        if gui_state := HimenaRelionGuiState.try_from_project_directory(cwd):
            can_open: list[Path] = []
            for job_id in gui_state.jobs_opened.get(get_user(), []):
                job_dir_path = cwd / job_id
                if job_dir_path.exists():
                    can_open.append(job_dir_path)
            n = len(can_open)

            if n > 0:
                s = "" if n == 1 else "s"
                ui.show_notification(
                    f"You have {n} opened job{s} in the last session.",
                    duration=8,
                    title="Recover Jobs?",
                    callbacks={"Open all": lambda: _open_jobs(ui, can_open)},
                )


def _open_jobs(ui: "MainWindow", can_open: list[Path]):
    for path in can_open:
        read_or_show_job(ui, path)


def on_himena_teardown(ui: "MainWindow"):
    """This function is called on himena teardown."""

    for dock in ui.dock_widgets:
        ids_opened: list[str] = []
        if not isinstance(dock.widget, QRelionPipelineFlowChart):
            continue
        relion_project_dir = dock.widget._relion_project_dir
        gui_state = HimenaRelionGuiState.from_project_directory(relion_project_dir)
        for i in dock.widget._tab_indices_from_this_pipeline():
            win = ui.tabs[i][0]
            if isinstance(job_dir := win.value, JobDirectory):
                ids_opened.append(job_dir.job_normal_id())
        if ids_opened:
            gui_state.jobs_opened[get_user()] = ids_opened
        gui_state.dump_to_project_directory(relion_project_dir)
