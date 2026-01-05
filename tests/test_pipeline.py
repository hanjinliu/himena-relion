from pathlib import Path
from himena import MainWindow
from ._utils import DEFAULT_PIPELINES_DIR

def test_reading_default_pipeline(himena_ui: MainWindow, tmpdir):
    path = Path(tmpdir) / "default_pipeline.star"
    txt = (DEFAULT_PIPELINES_DIR / "full.star").read_text()
    path.write_text(txt)
    himena_ui.read_file(path)

    txt = (DEFAULT_PIPELINES_DIR / "no_input.star").read_text()
    path.write_text(txt)
    himena_ui.read_file(path)
