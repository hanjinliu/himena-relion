from pathlib import Path
from himena import MainWindow
from himena.testing import choose_one_dialog_response

from himena_relion.pipeline.widgets import QRelionPipelineFlowChart, _list_jobs_for_palette
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
    flowchart = get_pipeline_widget(himena_ui)

    choices = _list_jobs_for_palette(flowchart._flow_chart._pipeline)
    with choose_one_dialog_response(himena_ui, choices[1][1]):
        flowchart._set_root_job()
    flowchart._refresh_flowchart()
    flowchart._unset_root_job()
