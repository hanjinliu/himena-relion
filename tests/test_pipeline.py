from pathlib import Path
from himena import MainWindow

import shutil
import time
from qtpy import QtCore
import threading
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5_tomo._continues import Refine3DTomoContinue
from himena_relion._widgets._job_edit import ScheduleMode, ContinueMode, EditMode
from himena_relion.pipeline.widgets import QRelionPipelineFlowChart, _list_jobs_for_palette
from himena_relion.pipeline_watcher import run_watcher, _WATCHER_FILE_NAME
from himena_relion._utils import update_default_pipeline
from himena_relion.io import _impl
from ._utils import DEFAULT_PIPELINES_DIR, JOBS_DIR_TOMO

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

def test_schedule_job(
    tmpdir,
    himena_ui,
    monkeypatch,
):
    monkeypatch.setattr("himena_relion.pipeline_watcher.execute_job", lambda *args, **kwargs: None)
    monkeypatch.setattr("himena_relion._job_class._run_relion_pipeliner_add_job_from_star", lambda *args, **kwargs: None)
    rln_dir = Path(tmpdir)
    rln_dir.joinpath("default_pipeline.star").write_text((DEFAULT_PIPELINES_DIR / "full.star").read_text())
    shutil.copytree(JOBS_DIR_TOMO / "Refine3D" / "job001", rln_dir / "Refine3D" / "job001")
    job_dir = JobDirectory(rln_dir / "Refine3D" / "job001")
    job_cls = job_dir._to_job_class()
    scheduler = job_cls._show_scheduler_widget(himena_ui, {}, cwd=rln_dir)
    assert type(scheduler._mode) is ScheduleMode
    scheduler._exec_btn.click()

def test_continue_job(
    tmpdir,
    himena_ui,
    monkeypatch,
):
    monkeypatch.setattr("himena_relion.pipeline_watcher.execute_job", lambda *args, **kwargs: None)

    rln_dir = Path(tmpdir)
    rln_dir.joinpath("default_pipeline.star").write_text((DEFAULT_PIPELINES_DIR / "full.star").read_text())
    shutil.copytree(JOBS_DIR_TOMO / "Refine3D" / "job001", rln_dir / "Refine3D" / "job001")
    job_dir = JobDirectory(rln_dir / "Refine3D" / "job001")
    job_dir.path.joinpath("job_pipeline.star").write_text((DEFAULT_PIPELINES_DIR / "full.star").read_text())
    job_dir.path.joinpath("run_it000_optimiser.star").write_text("")
    job_cls_cont = Refine3DTomoContinue(job_dir)
    scheduler = job_cls_cont._show_scheduler_widget_for_continue(
        himena_ui,
        {
            "fn_cont": "Refine3D/job001/run_it000_optimiser.star",
            "_job_dir": job_dir,
        }
    )
    assert type(scheduler._mode) is ContinueMode
    scheduler._exec_btn.click()

def test_overwrite_job(
    tmpdir,
    himena_ui,
    monkeypatch,
):
    monkeypatch.setattr("himena_relion.pipeline_watcher.execute_job", lambda *args, **kwargs: None)

    rln_dir = Path(tmpdir)
    rln_dir.joinpath("default_pipeline.star").write_text((DEFAULT_PIPELINES_DIR / "full.star").read_text())
    shutil.copytree(JOBS_DIR_TOMO / "Refine3D" / "job001", rln_dir / "Refine3D" / "job001")
    job_dir = JobDirectory(rln_dir / "Refine3D" / "job001")
    job_dir.path.joinpath("job_pipeline.star").write_text((DEFAULT_PIPELINES_DIR / "full.star").read_text())
    scheduler = _impl.overwrite_relion_job(himena_ui, job_dir)
    assert type(scheduler._mode) is EditMode
    scheduler._exec_btn.click()
