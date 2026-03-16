from typing import Callable

from himena import MainWindow

from himena_relion.startup import on_himena_startup

def test_startup(make_himena_ui: Callable[[], MainWindow]):
    ui = make_himena_ui("qt")
    on_himena_startup(ui)
