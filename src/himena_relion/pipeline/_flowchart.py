from __future__ import annotations
from pathlib import Path
from qtpy import QtGui, QtCore, QtWidgets as QtW
from cmap import Color

from himena import MainWindow
from himena.exceptions import Cancelled
from himena.qt._qflowchart import QFlowChartView, BaseNodeItem
from himena_relion.consts import JOB_ID_MAP, RelionJobState
from himena_relion._utils import read_or_show_job
from himena_relion._pipeline import RelionDefaultPipeline, RelionJobInfo, NodeStatus
from himena_relion._job_dir import ExternalJobDirectory, JobDirectory
from himena_relion.io import _impl


class QRelionPipelineFlowChartView(QFlowChartView):
    def __init__(self, ui: MainWindow, scene):
        super().__init__(scene)
        self.item_right_clicked.connect(self._on_right_clicked)
        self._ui = ui
        self._pipeline = RelionDefaultPipeline.empty()
        self._relion_project_dir: Path = Path.cwd()
        self.item_left_double_clicked.connect(self._on_item_double_clicked)
        self.item_left_clicked.connect(self._update_selection_rect)
        self._last_selection_highlight_rect = None
        self._dodge_distance = 64
        self._id_added = set()

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
        self._id_added.clear()

        # If the flowchart has been dragged, item positions are different from default.
        # Restore old positions
        new_infos: list[RelionJobInfo] = []
        for info in pipeline._nodes:
            if info.path in old_positions:
                self._add_job_node_item(info)
            else:
                new_infos.append(info)
        for new_item in self._node_map.values():
            if pos := old_positions.get(new_item.item().id()):
                new_item.setPos(pos)
        # new items should be added last to adjust their positions properly
        default_pos = next(iter(old_positions.values()), QtCore.QPointF(0, 0))
        for new_info in new_infos:
            new_item = self._add_job_node_item(new_info)
            new_item.setPos(default_pos)

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
        if item.id() not in self._id_added:
            qitem = self.add_child(item, parents=parents)
            self._id_added.add(item.id())
        else:
            qitem = self._node_map[item.id()]
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
            read_or_show_job(self._ui, path)
        else:
            raise FileNotFoundError(f"File {path} does not exist.")

    def center_on_item(self, item: RelionJobNodeItem):
        if node := self._node_map.get(item.id()):
            center = node.center()
            self.centerOn(center)
            node.setSelected(True)

    def _on_right_clicked(self, item: RelionJobNodeItem):
        menu = self._prep_right_click_menu(item)
        menu.exec(QtGui.QCursor.pos())

    def _prep_right_click_menu(self, item: RelionJobNodeItem):
        if node := self._node_map.get(item.id()):
            node.setSelected(True)
        path = self._relion_project_dir / item.id() / "job.star"
        job_dir = JobDirectory.from_job_star(path)
        state = job_dir.state()
        menu = QtW.QMenu(self)
        submenu_open = menu.addMenu("Open")
        submenu_cleanup = menu.addMenu("Cleanup")
        submenu_open.addAction(
            "Open job.star as text",
            lambda: _impl.open_relion_job_star(self._ui, job_dir),
        )
        submenu_open.addAction(
            "Open job_pipeline.star as text",
            lambda: _impl.open_relion_job_pipeline_star(self._ui, job_dir),
        )
        action = submenu_cleanup.addAction(
            "Gentle clean", lambda: _impl.gentle_clean_relion_job(self._ui, job_dir)
        )
        action.setEnabled(state is RelionJobState.EXIT_SUCCESS)
        action = submenu_cleanup.addAction(
            "Harsh clean", lambda: _impl.harsh_clean_relion_job(self._ui, job_dir)
        )
        action.setEnabled(state is RelionJobState.EXIT_SUCCESS)
        menu.addAction("Mark as finished", lambda: _impl.mark_as_finished(job_dir))
        action.setEnabled(state is not RelionJobState.EXIT_SUCCESS)
        menu.addAction("Mark as failed", lambda: _impl.mark_as_failed(job_dir))
        action.setEnabled(state is not RelionJobState.EXIT_FAILURE)
        menu.addSeparator()
        action = menu.addAction(
            "Abort", _ignore_cancel(_impl.abort_relion_job, self._ui, job_dir)
        )
        action.setEnabled(state is RelionJobState.RUNNING)
        menu.addAction(
            "Overwrite ...", lambda: _impl.overwrite_relion_job(self._ui, job_dir)
        )
        menu.addAction("Clone ...", lambda: _impl.clone_relion_job(self._ui, job_dir))
        menu.addAction(
            "Set Alias ...", _ignore_cancel(_impl.set_job_alias, self._ui, job_dir)
        )
        menu.addSeparator()
        action = menu.addAction(
            "Trash", _ignore_cancel(_impl.trash_job, self._ui, job_dir)
        )
        action.setEnabled(state is not RelionJobState.RUNNING)
        return menu


def _ignore_cancel(func, *args, **kwargs):
    """Decorator to ignore Cancelled exception."""

    def wrapper():
        try:
            return func(*args, **kwargs)
        except Cancelled:
            pass

    return wrapper


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
