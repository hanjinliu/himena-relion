from typing import Callable
import os
from himena import MainWindow
from pathlib import Path
from himena_relion.startup import on_himena_startup, _WATCHER_FILE_NAME

def test_startup(make_himena_ui: Callable[[], MainWindow], tmpdir):
    os.chdir(tmpdir)
    Path(tmpdir).joinpath(_WATCHER_FILE_NAME).write_text(
        '{"pid": 999999, "user": "test_user"}'
    )
    ui = make_himena_ui("qt")
    on_himena_startup(ui)
