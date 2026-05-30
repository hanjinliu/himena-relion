"""Useful startup function to use himena with RELION."""

from typing import TYPE_CHECKING

from pathlib import Path
import json
import psutil
from himena_relion._job_class import scheduler_widget
from himena_relion._utils import get_pipeline_widgets
from himena_relion.pipeline_watcher import _WATCHER_FILE_NAME

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
                js = json.loads(lock.read_text())
                pid = js["pid"]
            except Exception:
                ui.show_notification(
                    f"Pipeline watcher lock file {_WATCHER_FILE_NAME} seems broken. "
                    "This lock will be removed."
                )
                lock.unlink()
                return
            try:
                process_name = psutil.Process(pid).name()
            except psutil.NoSuchProcess:
                process_name = ""
            else:
                if process_name != "himena-relion":
                    ui.show_notification(
                        f"Pipeline watcher lock file {_WATCHER_FILE_NAME} found, but "
                        "the process seems not running. This lock will be removed."
                    )
