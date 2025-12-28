from __future__ import annotations
from pathlib import Path
from qtpy import QtGui, QtCore
from cmap import Color

from himena import MainWindow
from himena.types import is_subtype
from himena.qt._qflowchart import QFlowChartView, BaseNodeItem
from himena_relion.consts import Type, JOB_ID_MAP
from himena_relion._pipeline import RelionDefaultPipeline, RelionJobInfo, NodeStatus
from himena_relion._job_dir import ExternalJobDirectory, JobDirectory


class QRelionPipelineFlowChartView(QFlowChartView):
    def __init__(self, ui: MainWindow, scene):
        super().__init__(scene)
        # self.item_right_clicked.connect(self._on_right_clicked)
        self._ui = ui
        self._pipeline = RelionDefaultPipeline([])
        self._relion_project_dir: Path = Path.cwd()
        self.item_left_double_clicked.connect(self._on_item_double_clicked)
        self.item_left_clicked.connect(self._update_selection_rect)
        self._last_selection_highlight_rect = None

    def set_pipeline(self, pipeline: RelionDefaultPipeline) -> None:
        if not isinstance(pipeline, RelionDefaultPipeline):
            raise TypeError("Model value must be a RelionDefaultPipeline.")
        self._pipeline = pipeline
        old_positions = {
            node.item().id(): node.pos() for node in self._node_map.values()
        }
        # clear all
        self.scene().clear()
        self._node_map.clear()

        # If the flowchart has been dragged, item positions are different from default.
        # Restore old positions
        new_infos = []
        for info in pipeline._nodes:
            if info.path in old_positions:
                self._add_job_node_item(info)
            else:
                new_infos.append(info)
        for new_item in self._node_map.values():
            if pos := old_positions.get(new_item.item().id()):
                new_item.setPos(pos)
        # new items should be added last to adjust their positions properly
        for new_info in new_infos:
            self._add_job_node_item(new_info)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self.viewport())
        pen = QtGui.QPen(QtGui.QColor(255, 84, 84), 3, QtCore.Qt.PenStyle.DotLine)
        painter.setPen(pen)
        for item in self.scene().selectedItems():
            rect = self.mapFromScene(item.sceneBoundingRect()).boundingRect()
            rect.adjust(-2, -2, 2, 2)
            painter.drawRect(rect)
            self._last_selection_highlight_rect = rect
        painter.end()

    def _add_job_node_item(self, info: RelionJobInfo):
        parents: list[Path] = []
        for parent in info.parents:
            parent_info = parent.node
            if parent_info.path not in self._node_map:
                self._add_job_node_item(parent_info)
            if parent_info.path not in parents:
                parents.append(parent_info.path)
        item = RelionJobNodeItem(info)
        qitem = self.add_child(item, parents=parents)
        return qitem

    def _on_item_double_clicked(self, item: RelionJobNodeItem):
        self._show_item_by_id(item.id())

    def mousePressEvent(self, event):
        self._update_selection_rect()
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self._update_selection_rect()
        return super().mouseMoveEvent(event)

    def _update_selection_rect(self):
        if self._last_selection_highlight_rect:
            self.update(self._last_selection_highlight_rect.adjusted(-5, -5, 5, 5))

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
            return f"{jobxxx}: {alias}\n({title})"
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
                return Color("khaki")
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
