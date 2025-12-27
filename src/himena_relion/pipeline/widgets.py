from __future__ import annotations
from collections import defaultdict
from pathlib import Path

import logging
from qtpy import QtGui, QtWidgets as QtW, QtCore
from cmap import Color
from superqt import QSearchableComboBox
from superqt.utils import thread_worker, GeneratorWorker
from watchfiles import watch, Change

from himena import MainWindow, WidgetDataModel
from himena.plugins import validate_protocol
from himena.style import Theme
from himena_relion._job_class import execute_job
from himena_relion._widgets._job_widgets import QJobPipelineViewer
from himena_relion.consts import Type, JOB_ID_MAP
from himena_relion._pipeline import (
    NodeStatus,
    RelionDefaultPipeline,
    RelionJobInfo,
    is_all_inputs_ready,
)
from himena_relion.pipeline._flowchart import (
    QRelionPipelineFlowChartView,
    RelionJobNodeItem,
)

_LOGGER = logging.getLogger(__name__)


class QRelionPipelineFlowChart(QtW.QWidget):
    """Widget to display RELION pipeline flow chart and manage scheduling."""

    update_required = QtCore.Signal(RelionDefaultPipeline)

    def __init__(self, ui: MainWindow):
        super().__init__()
        self._directory_label = QtW.QLabel("RELION Pipeline Flow Chart", self)
        self._scene = QtW.QGraphicsScene()

        self._flow_chart = QRelionPipelineFlowChartView(ui, self._scene)
        self._finder = QSearchableComboBox(self)
        self._footer = QJobPipelineViewer()
        self._watcher: GeneratorWorker | None = None
        layout = QtW.QVBoxLayout(self)
        splitter = QtW.QSplitter(QtCore.Qt.Orientation.Vertical)
        splitter.addWidget(self._flow_chart)
        splitter.addWidget(self._footer)
        splitter.setSizes([800, 420])

        layout.addWidget(self._directory_label)
        layout.addWidget(self._finder)
        layout.addWidget(splitter)

        self._finder.activated.connect(self._move_to_job)
        self._finder.lineEdit().setPlaceholderText("Find job...")

        self._flow_chart.item_left_clicked.connect(self._on_item_left_clicked)
        self._flow_chart.background_left_clicked.connect(
            self._on_background_left_clicked
        )

        self._state_to_job_map = defaultdict[NodeStatus, dict[str, RelionJobInfo]](dict)
        self.update_required.connect(self._on_pipeline_updated)
        self.update_required.connect(self._on_job_state_changed)

    def sizeHint(self):
        return QtCore.QSize(350, 600)

    def _on_item_left_clicked(self, item: RelionJobNodeItem):
        job_dir = item.job_dir(self._flow_chart._relion_project_dir)
        self._footer.initialize(job_dir)
        self._footer.update_item_colors(job_dir)

    def _on_background_left_clicked(self):
        self._footer.clear_in_out()

    @validate_protocol
    def update_model(self, model: WidgetDataModel) -> None:
        if not isinstance(src := model.source, Path):
            raise TypeError("RELION default_pipeline.star source file not found.")
        assert isinstance(model.value, RelionDefaultPipeline)
        self.widget_closed_callback()
        self._on_pipeline_updated(model.value)
        self._flow_chart._relion_project_dir = src.parent
        parts = src.parts
        if len(parts) >= 3:
            self._directory_label.setText(f"{parts[-3]}/{parts[-2]}/")
        else:
            self._directory_label.setText(f"{parts[-2]}/")
        self._watcher = self._watch_default_pipeline_star(src)
        self._state_to_job_map.clear()
        for job in model.value.iter_nodes():
            _dict = self._state_to_job_map[job.status]
            _dict[job.path.as_posix()] = job

    def _on_pipeline_updated(self, pipeline: RelionDefaultPipeline) -> None:
        self._flow_chart.set_pipeline(pipeline)
        self._update_finder()

    @validate_protocol
    def model_type(self) -> str:
        return Type.RELION_PIPELINE

    @validate_protocol
    def size_hint(self):
        hint = self.sizeHint()
        return (hint.width(), hint.height())

    @validate_protocol
    def theme_changed_callback(self, theme: Theme) -> None:
        self._flow_chart.setBackgroundBrush(QtGui.QColor(Color(theme.background).hex))

    @validate_protocol
    def widget_closed_callback(self) -> None:
        if self._watcher:
            self._watcher.quit()
            self._watcher = None

    def closeEvent(self, a0):
        self.widget_closed_callback()
        return super().closeEvent(a0)

    def _update_finder(self):
        self._finder.clear()
        pipeline = self._flow_chart._pipeline
        for info in pipeline.iter_nodes():
            jobxxx = info.path.stem
            if jobxxx.startswith("job"):
                jobxxx = jobxxx[3:]
            state = info.status.value.title()
            title = JOB_ID_MAP.get(info.type_label, info.type_label)
            if info.alias:
                title = f"{info.alias} ({title})"
            display_text = f"{jobxxx}: {title} [{state}]"
            self._finder.addItem(display_text, info)  # text, userData
        self._finder.setCurrentText("")
        self._finder_initialized = True

    def _move_to_job(self, index: int):
        if isinstance(info := self._finder.itemData(index), RelionJobInfo):
            for node in self._flow_chart._node_map.values():
                item = node.item()
                assert isinstance(item, RelionJobNodeItem)
                if item._job == info:
                    self._flow_chart.center_on_item(item)
                    return

    @thread_worker(start_thread=True)
    def _watch_default_pipeline_star(self, path: Path):
        """Watch the job directory for changes."""
        for changes in watch(path, rust_timeout=400, yield_on_timeout=True):
            if self._watcher is None:
                _LOGGER.info("Pipeline watcher stopped.")
                return  # stopped
            for change, fp in changes:
                if change == Change.deleted:
                    continue
                _LOGGER.info("default_pipeline.star updated.")
                try:
                    pipeline = RelionDefaultPipeline.from_pipeline_star(path)
                except Exception:
                    _LOGGER.warning(
                        "Failed to read default_pipeline.star", exc_info=True
                    )
                else:
                    # Update the internal data (thus, the flow chart)
                    self.update_required.emit(pipeline)
            yield

    def _on_job_state_changed(self, pipeline: RelionDefaultPipeline) -> None:
        success_old = self._state_to_job_map[NodeStatus.SUCCEEDED]
        failed_old = self._state_to_job_map[NodeStatus.FAILED]
        self._state_to_job_map.clear()
        for job in pipeline.iter_nodes():
            _dict = self._state_to_job_map[job.status]
            _dict[job.path.as_posix()] = job
        success_new = self._state_to_job_map[NodeStatus.SUCCEEDED]
        failed_new = self._state_to_job_map[NodeStatus.FAILED]
        ui = self._flow_chart._ui
        # Notify newly succeeded jobs and run scheduled jobs
        if succeeded := set(success_new.keys()) - set(success_old.keys()):
            for job in self._state_to_job_map[NodeStatus.SCHEDULED].values():
                # run all the scheduled jobs whose dependencies are met
                if is_all_inputs_ready(job.path):
                    execute_job(job.path.as_posix(), ignore_error=True)
                    ui.show_notification(f"Scheduled job {job.job_repr()} started.")
            ui.show_notification(
                "\n".join(f"Job {job}/ succeeded." for job in succeeded)
            )

        # Notify newly failed jobs
        if failed := set(failed_new.keys()) - set(failed_old.keys()):
            ui.show_notification("\n".join(f"Job {job}/ failed." for job in failed))
