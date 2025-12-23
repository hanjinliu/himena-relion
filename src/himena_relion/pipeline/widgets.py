from __future__ import annotations
from collections import defaultdict
from pathlib import Path

import logging
from qtpy import QtGui, QtWidgets as QtW, QtCore
from cmap import Color
from superqt import ensure_main_thread, QSearchableComboBox
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

        layout.addWidget(self._directory_label)
        layout.addWidget(self._finder)
        layout.addWidget(splitter)

        self._finder.activated.connect(self._move_to_job)
        self._finder.lineEdit().setPlaceholderText("Find job...")

        self._flow_chart.item_left_clicked.connect(self._on_item_left_clicked)
        self._flow_chart.background_left_clicked.connect(
            self._on_background_left_clicked
        )

        self._state_to_job_map = defaultdict[NodeStatus, set[RelionJobInfo]](set)

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
        self.widget_closed_callback()
        self._on_pipeline_updated(model)
        self._flow_chart._relion_project_dir = src.parent
        parts = src.parts
        if len(parts) >= 3:
            self._directory_label.setText(f"{parts[-3]}/{parts[-2]}/")
        else:
            self._directory_label.setText(f"{parts[-2]}/")
        self._watcher = self._watch_default_pipeline_star(src)
        self._update_finder()
        self._finder.setCurrentText("")

    @ensure_main_thread
    def _on_pipeline_updated(self, model: WidgetDataModel) -> None:
        current_center_pos = self._flow_chart.mapToScene(
            self._flow_chart.viewport().rect().center()
        )
        self._flow_chart.clear_all()
        self._flow_chart.add_pipeline(model.value)
        self._flow_chart.centerOn(current_center_pos)

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
            display_text = (
                f"{jobxxx}: {JOB_ID_MAP.get(info.type_label, info.type_label)}"
            )
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
    def _watch_default_pipeline_star(self, path):
        """Watch the job directory for changes."""
        for changes in watch(path, rust_timeout=400, yield_on_timeout=True):
            if self._watcher is None:
                return  # stopped
            for change, fp in changes:
                if change == Change.deleted:
                    continue
                _LOGGER.info("default_pipeline.star updated.")
                try:
                    pipeline = RelionDefaultPipeline.from_pipeline_star(path)
                except Exception as e:
                    _LOGGER.warning("Failed to read default_pipeline.star: %s", e)
                else:
                    success_old = self._state_to_job_map[NodeStatus.SUCCEEDED]
                    self._state_to_job_map.clear()
                    for job in pipeline.iter_nodes():
                        self._state_to_job_map[job.status].add(job)
                    success_new = self._state_to_job_map[NodeStatus.SUCCEEDED]
                    if success_new - success_old:
                        for job in self._state_to_job_map[NodeStatus.SCHEDULED]:
                            # run all the scheduled jobs whose dependencies are met
                            if is_all_inputs_ready(job.path):
                                execute_job(job.path.as_posix(), ignore_error=True)
                                self._flow_chart._ui.show_notification(
                                    f"Scheduled job {job.path} started."
                                )

                    # update the internal data (thus, the flow chart)
                    model = WidgetDataModel(
                        value=pipeline,
                        type=Type.RELION_PIPELINE,
                        title="RELION Pipeline",
                    )
                    self._on_pipeline_updated(model)
            yield
