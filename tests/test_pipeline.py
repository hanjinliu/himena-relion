from pathlib import Path
from himena import MainWindow

import time
from qtpy import QtCore
import threading
from himena_relion.pipeline.widgets import QRelionPipelineFlowChart, _list_jobs_for_palette
from himena_relion.pipeline_watcher import run_watcher, _WATCHER_FILE_NAME
from himena_relion._utils import update_default_pipeline
from ._utils import DEFAULT_PIPELINES_DIR

def test_reading_default_pipeline(himena_ui: MainWindow, tmpdir):
    path = Path(tmpdir) / "default_pipeline.star"
    txt = (DEFAULT_PIPELINES_DIR / "full.star").read_text()
    path.write_text(txt)
    himena_ui.read_file(path)
    flowchart = get_pipeline_widget(himena_ui)
    assert flowchart._stacked_widget.currentWidget() == flowchart._flow_chart

    txt = (DEFAULT_PIPELINES_DIR / "no_input.star").read_text()
    path.write_text(txt)
    himena_ui.read_file(path)
    flowchart = get_pipeline_widget(himena_ui)
    assert flowchart._stacked_widget.currentWidget() == flowchart._flow_chart

def test_empty_default_pipeline(himena_ui: MainWindow, tmpdir):
    path = Path(tmpdir) / "default_pipeline.star"
    path.write_text("")
    himena_ui.read_file(path)
    flowchart = get_pipeline_widget(himena_ui)
    assert flowchart._stacked_widget.currentWidget() == flowchart._start_screen

def get_pipeline_widget(himena_ui: MainWindow) -> QRelionPipelineFlowChart:
    for dock in himena_ui.dock_widgets:
        if isinstance(dock.widget, QRelionPipelineFlowChart):
            return dock.widget
    raise RuntimeError("Pipeline widget not found")

def test_reading_default_pipeline_during_filtering(himena_ui: MainWindow, tmpdir):
    path = Path(tmpdir) / "default_pipeline.star"
    txt = (DEFAULT_PIPELINES_DIR / "full.star").read_text()
    path.write_text(txt)
    himena_ui.read_file(path)
    pipeline_widget = get_pipeline_widget(himena_ui)

    _list_jobs_for_palette(pipeline_widget._flow_chart._pipeline)
    pipeline_widget._refresh_flowchart()
    pipeline_widget._open_all_running_jobs()
    pipeline_widget._open_last_completed_job()

    pipeline_widget._center_on_item(Path("MotionCorr/job002/"))
    pipeline_widget._switch_mode()
    pipeline_widget._center_on_item(Path("MotionCorr/job002/"))

    table_view = pipeline_widget._table_view
    table_view._sort_by_widget_mgui.value = "Time"
    table_view._sort_ascending_btn.click()

    index00 = table_view._table_view._model.index(0, 0)
    index02 = table_view._table_view._model.index(0, 2)
    table_view._table_view._model.data(index00, QtCore.Qt.ItemDataRole.DisplayRole)
    table_view._table_view._model.data(index00, QtCore.Qt.ItemDataRole.ToolTipRole)
    table_view._table_view._model.data(index00, QtCore.Qt.ItemDataRole.DecorationRole)
    table_view._table_view._model.data(index02, QtCore.Qt.ItemDataRole.DecorationRole)

def test_pipeline_watcher(tmpdir):
    rlndir = Path(tmpdir)
    path = rlndir / "default_pipeline.star"
    # NOTE: CtfFind/job003/ is scheduled
    txt = (DEFAULT_PIPELINES_DIR / "full.star").read_text()
    path.write_text(txt)

    with path.open("r+") as f:
        update_default_pipeline(f, "MotionCorr/job002/", "Running")

    thread = threading.Thread(target=run_watcher, args=(str(rlndir),), daemon=True)
    thread.start()
    time.sleep(0.3)
    assert rlndir.joinpath(_WATCHER_FILE_NAME).exists()
    with path.open("r+") as f:
        update_default_pipeline(f, "CtfFind/job003/", "Succeeded")
    thread.join(timeout=0.5)
    assert not rlndir.joinpath(_WATCHER_FILE_NAME).exists()

def test_pipeline_watcher_exit(tmpdir):
    rlndir = Path(tmpdir)
    path = rlndir / "default_pipeline.star"
    # NOTE: CtfFind/job003/ is scheduled
    txt = (DEFAULT_PIPELINES_DIR / "full.star").read_text()
    path.write_text(txt)

    thread = threading.Thread(target=run_watcher, args=(str(rlndir),), daemon=True)
    thread.start()
    time.sleep(0.3)
    assert not rlndir.joinpath(_WATCHER_FILE_NAME).exists()
    with path.open("r+") as f:
        update_default_pipeline(f, "CtfFind/job003/", "Succeeded")
    thread.join(timeout=0.5)
    assert not rlndir.joinpath(_WATCHER_FILE_NAME).exists()
