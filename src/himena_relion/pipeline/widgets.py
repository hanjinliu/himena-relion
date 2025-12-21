from __future__ import annotations
from pathlib import Path

import logging
from qtpy import QtGui, QtWidgets as QtW, QtCore
from cmap import Color
from superqt import ensure_main_thread, QSearchableComboBox
from superqt.utils import thread_worker, GeneratorWorker
from watchfiles import watch, Change

from himena import MainWindow, WidgetDataModel
from himena.types import is_subtype
from himena.qt._qflowchart import QFlowChartView, BaseNodeItem
from himena.plugins import validate_protocol
from himena.style import Theme
from himena_relion._widgets._job_widgets import QJobPipelineViewer
from himena_relion.consts import Type, JOB_ID_MAP
from himena_relion._pipeline import RelionDefaultPipeline, RelionJobInfo, NodeStatus
from himena_relion._job import ExternalJobDirectory, JobDirectory

_LOGGER = logging.getLogger(__name__)


class QRelionPipelineFlowChart(QtW.QWidget):
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
                    model = WidgetDataModel(
                        value=pipeline,
                        type=Type.RELION_PIPELINE,
                        title="RELION Pipeline",
                    )
                    self._on_pipeline_updated(model)
            yield


class QRelionPipelineFlowChartView(QFlowChartView):
    def __init__(self, ui: MainWindow, scene):
        super().__init__(scene)
        # self.view.item_right_clicked.connect(self._on_right_clicked)
        self._ui = ui
        self._pipeline = RelionDefaultPipeline([])
        self._relion_project_dir: Path = Path.cwd()
        self.item_left_double_clicked.connect(self._on_item_double_clicked)

    def add_pipeline(self, pipeline: RelionDefaultPipeline) -> None:
        if not isinstance(pipeline, RelionDefaultPipeline):
            raise TypeError("Model value must be a RelionDefaultPipeline.")
        self._pipeline = pipeline
        for info in pipeline._nodes:
            if info.path not in self._node_map:
                self._add_job_node_item(info)

    def clear_all(self) -> None:
        self.scene().clear()
        self._node_map.clear()

    def _add_job_node_item(self, info: RelionJobInfo) -> None:
        parents: list[Path] = []
        for parent in info.parents:
            parent_info = parent.node
            if parent_info.path not in self._node_map:
                self._add_job_node_item(parent_info)
            if parent_info.path not in parents:
                parents.append(parent_info.path)
        item = RelionJobNodeItem(info)
        self.add_child(item, parents=parents)

    def _on_item_double_clicked(self, item: RelionJobNodeItem):
        self._show_item_by_id(item.id())

    def _show_item_by_id(self, item_id: Path):
        """Open the job directory or activate the already opened one."""
        path = self._relion_project_dir / item_id
        if path.exists():
            # if already opened, switch to it
            for i_tab, tab in self._ui.tabs.enumerate():
                for i_window, window in tab.enumerate():
                    if not is_subtype(window.model_type(), Type.RELION_JOB):
                        continue
                    try:
                        val = window.value
                        if isinstance(val, JobDirectory) and path == val.path:
                            self._ui.tabs.current_index = i_tab
                            tab.current_index = i_window
                            return
                    except Exception:
                        continue
            self._ui.read_file(path)
        else:
            raise FileNotFoundError(f"File {path} does not exist.")

    def center_on_item(self, item: RelionJobNodeItem):
        if node := self._node_map.get(item.id()):
            center = node.center()
            self.centerOn(center)
            node.setSelected(True)


class RelionJobNodeItem(BaseNodeItem):
    def __init__(self, job: RelionJobInfo):
        self._job = job

    def text(self) -> str:
        """Return the text of the node"""
        jobxxx = self._job.path.stem
        if jobxxx.startswith("job"):
            jobxxx = jobxxx[3:]
        if self._job.type_label == "relion.external":
            title = ExternalJobDirectory(self._job.path).job_title()
        else:
            title = JOB_ID_MAP.get(self._job.type_label, self._job.type_label)
        if alias := self._job.alias:
            return f"{jobxxx}: {title}\n{alias}"
        return f"{jobxxx}: {title}"

    def color(self):
        """Return the color of the node"""
        match self._job.status:
            case NodeStatus.SUCCEEDED:
                return Color("lightgreen")
            case NodeStatus.FAILED:
                return Color("lightcoral")
            case NodeStatus.ABORTED:
                return Color("lightyellow")
            case NodeStatus.RUNNING:
                return Color("lightblue")
            case NodeStatus.SCHEDULED:
                return Color("orange")
            case _:
                return Color("lightgray")

    def tooltip(self) -> str:
        """Return the tooltip text for the node"""
        return f"Status: {self._job.status.value.capitalize()}"

    def id(self):
        """Return a unique identifier for the node"""
        return self._job.path

    def content(self) -> str:
        """Return the content of the node, default is the text"""
        return self.text()

    def job_dir(self, relion_dir: Path) -> JobDirectory:
        """Return the job directory"""
        return JobDirectory(relion_dir / self._job.path)
