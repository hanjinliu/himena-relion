from typing import Callable
import os
from himena import MainWindow
from pathlib import Path
from himena_relion.pipeline._gui_state import HimenaRelionGuiState
from himena_relion.startup import on_himena_startup, on_himena_teardown, _WATCHER_FILE_NAME

_GUI_STATE_TEXT = """{
  "jobs": {
    "CtfFind/job003/": {"tags": [0, 1]},
    "ExcludeTiltImages/job004/": {"tags": [1]},
    "Tomograms/job006/": {"tags": [1]}
  },
  "tag_choices": [
    {"name": "first", "color": "#40E0D0", "id": "dd22fbce-6e1c-414f-8ee2-f2f4620a7351"},
    {"name": "Tag-2", "color": "#DDA0DD", "id": "927e4b5c-4324-41e3-8fda-b9577d47d5bd"}
  ],
  "jobs_opened": {"abc": ["Class3D/job099/"]},
  "version": "0.0.3"
}
"""

def test_startup(make_himena_ui: Callable[[], MainWindow], tmpdir):
    os.chdir(tmpdir)
    Path(tmpdir).joinpath(_WATCHER_FILE_NAME).write_text(
        '{"pid": 999999, "user": "test_user"}'
    )
    Path(tmpdir).joinpath("default_pipeline.star").write_text("")
    state = HimenaRelionGuiState.model_validate_json(_GUI_STATE_TEXT)
    state.dump_to_project_directory(tmpdir)
    ui = make_himena_ui("qt")
    on_himena_startup(ui)
    on_himena_teardown(ui)
