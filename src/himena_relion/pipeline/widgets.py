from __future__ import annotations
from pathlib import Path

from himena import MainWindow, WidgetDataModel
from qtpy import QtGui, QtWidgets as QtW, QtCore
from cmap import Color
from himena.qt._qflowchart import QFlowChartWidget, BaseNodeItem
from himena.plugins import validate_protocol
from himena.style import Theme
from himena_relion.consts import Type, JOB_ID_MAP
from himena_relion._pipeline import RelionDefaultPipeline, RelionJobInfo, NodeStatus


class RelionJobNodeItem(BaseNodeItem):
    def __init__(self, job: RelionJobInfo):
        self._job = job

    def text(self) -> str:
        """Return the text of the node"""
        jobxxx = self._job.path.stem
        if jobxxx.startswith("job"):
            jobxxx = jobxxx[3:]
        title = JOB_ID_MAP.get(self._job.type_label, self._job.type_label)
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


class QRelionPipelineFlowChart(QtW.QWidget):
    def __init__(self, ui: MainWindow):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        self._directory_label = QtW.QLabel("RELION Pipeline Flow Chart", self)
        self._flow_chart = QRelionPipelineFlowChartView(ui)
        layout.addWidget(self._directory_label)
        layout.addWidget(self._flow_chart)

    def sizeHint(self):
        return QtCore.QSize(320, 400)

    @validate_protocol
    def update_model(self, model: WidgetDataModel) -> None:
        if not isinstance(src := model.source, Path):
            raise TypeError("RELION project source not found.")
        self._flow_chart.clear_all()
        self._flow_chart.add_pipeline(model.value)
        self._flow_chart._relion_project_dir = src.parent
        self._directory_label.setText(f"/{src.parent.name}")

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._flow_chart._pipeline, type=Type.RELION_PIPELINE
        )

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


class QRelionPipelineFlowChartView(QFlowChartWidget):
    def __init__(self, ui: MainWindow):
        super().__init__()
        # self.view.item_right_clicked.connect(self._on_right_clicked)
        self._ui = ui
        self._pipeline = RelionDefaultPipeline([])
        self._relion_project_dir: Path = Path.cwd()
        self.view.item_left_double_clicked.connect(self._on_item_double_clicked)

    def add_pipeline(self, pipeline: RelionDefaultPipeline) -> None:
        self._pipeline = pipeline
        for info in pipeline._nodes:
            if info.path not in self.view._node_map:
                self._add_job_node_item(info)

    def clear_all(self) -> None:
        self.scene.clear()
        self.view._node_map.clear()

    def _add_job_node_item(self, info: RelionJobInfo) -> None:
        parents: list[Path] = []
        for parent in info.parents:
            parent_info = parent.node
            if parent_info.path not in self.view._node_map:
                self._add_job_node_item(parent_info)
            if parent_info.path not in parents:
                parents.append(parent_info.path)
        item = RelionJobNodeItem(info)
        self.view.add_child(item, parents=parents)

    def _on_item_double_clicked(self, item: RelionJobNodeItem):
        # open the item
        path = self._relion_project_dir / item.id()
        if path.exists():
            self._ui.read_file(path)
        else:
            raise FileNotFoundError(f"File {path} does not exist.")
