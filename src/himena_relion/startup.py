"""Useful startup function to use himena with RELION."""

from typing import TYPE_CHECKING

from pathlib import Path
from himena_relion._job_class import scheduler_widget

if TYPE_CHECKING:
    from himena.widgets import MainWindow


def on_himena_startup(ui: "MainWindow"):
    """This function is called on himena startup."""
    if (starpath := Path.cwd().joinpath("default_pipeline.star")).exists():
        print("RELION pipeline found, loading pipeline into application")
        ui.read_file(starpath, plugin="himena_relion.io.read_relion_pipeline")
        scheduler = scheduler_widget(ui)
        scheduler.clear_content()
        ui.size = max(ui.size.width, 1260), ui.size.height
