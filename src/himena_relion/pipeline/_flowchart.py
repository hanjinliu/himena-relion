from __future__ import annotations
from contextlib import suppress
from pathlib import Path
from qtpy import QtGui, QtCore, QtWidgets as QtW
from cmap import Color

from himena import MainWindow
from himena.exceptions import Cancelled
from himena.qt._qflowchart import QFlowChartView, BaseNodeItem
from himena.workflow import LocalReaderMethod
from himena_relion.consts import JOB_ID_MAP
from himena_relion._utils import read_or_show_job
from himena_relion._pipeline import RelionDefaultPipeline, RelionJobInfo, NodeStatus
from himena_relion._job_dir import ExternalJobDirectory, JobDirectory
from himena_relion._job_class import execute_job
from himena_relion.io import _impl


class QRelionPipelineFlowChartView(QFlowChartView):
    def __init__(self, ui: MainWindow, scene):
        super().__init__(scene)
        self._ui = ui
        self._pipeline = RelionDefaultPipeline.empty()
        self._relion_project_dir: Path = Path.cwd()

        self._last_selection_highlight_rect = None
        self._dodge_distance = 64
        self._id_added = set()
        self._root_job_info: RelionJobInfo | None = None

        # event connection
        self.item_right_clicked.connect(self._on_right_clicked)
        self.item_left_double_clicked.connect(self._on_item_double_clicked)
        self.item_left_clicked.connect(self._update_selection_rect)

    def set_pipeline(self, pipeline: RelionDefaultPipeline) -> None:
        if not isinstance(pipeline, RelionDefaultPipeline):
            raise TypeError("Model value must be a RelionDefaultPipeline.")
        self._pipeline = pipeline

        # self._root_job_info needs update because its parents/children may have changed
        if self._root_job_info is not None:
            for node in pipeline._nodes:
                if node.path == self._root_job_info.path:
                    self._root_job_info = node
                    break

        old_positions = {
            node.item().id(): node.pos() for node in self._node_map.values()
        }
        # clear all
        self.scene().clear()
        self._node_map.clear()
        self._id_added.clear()

        # Parents for filtering the flowchart
        if self._root_job_info is None:
            _allowed_parents = {node.path for node in pipeline._nodes}
        else:
            _allowed_parents = _track_children(self._root_job_info)

        # If the flowchart has been dragged, item positions are different from default.
        # Restore old positions
        new_infos: list[RelionJobInfo] = []
        for info in pipeline._nodes:
            if info.path in old_positions:
                self._add_job_node_item(info, _allowed_parents)
            else:
                new_infos.append(info)
        for new_item in self._node_map.values():
            if pos := old_positions.get(new_item.item().id()):
                new_item.setPos(pos)
        # new items should be added last to adjust their positions properly
        default_pos = next(iter(old_positions.values()), QtCore.QPointF(0, 0))
        for new_info in new_infos:
            if new_item := self._add_job_node_item(new_info, _allowed_parents):
                new_item.setPos(default_pos)

        # FIXME: Newly added node usually goes to a wrong place. Resetting positions
        # fixes this problem for some reason ...
        old_positions = {
            node.item().id(): node.pos() for node in self._node_map.values()
        }
        self.scene().clear()
        self._node_map.clear()
        self._id_added.clear()

        for info in pipeline._nodes:
            if info.path in old_positions:
                self._add_job_node_item(info, _allowed_parents)
        for new_item in self._node_map.values():
            if pos := old_positions.get(new_item.item().id()):
                new_item.setPos(pos)

    def set_root_job(self, root_job_info: RelionJobInfo | None):
        self._root_job_info = root_job_info
        self._node_map.clear()
        self._id_added.clear()
        self.set_pipeline(self._pipeline)
        if root_job_info and (node := self._node_map.get(root_job_info.path)):
            self.center_on_item(node.item())

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

    def _add_job_node_item(
        self,
        info: RelionJobInfo,
        allowed_parents: set[Path],
    ):
        if info.path not in allowed_parents:
            return None
        parents: list[Path] = []  # parent of incoming item
        for parent in info.parents:
            parent_info = parent.node
            if parent_info.path not in self._node_map:
                self._add_job_node_item(parent_info, allowed_parents)
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
        """Move the view to ensure the item visible and select it."""
        if node := self._node_map.get(item.id()):
            center = node.center()
            self.centerOn(center)
            node.setSelected(True)
        else:
            self._ui.show_notification("Job not found in the flowchart.")

    def _on_right_clicked(self, item: RelionJobNodeItem):
        menu = self._prep_right_click_menu(item)
        menu.exec(QtGui.QCursor.pos())

    def _prep_right_click_menu(self, item: RelionJobNodeItem):
        if node := self._node_map.get(item.id()):
            node.setSelected(True)
        path = self._relion_project_dir / item.id() / "job.star"

        def get_job():
            return JobDirectory.from_job_star(path)

        status = item._job.status
        menu = QtW.QMenu(self)
        menu.setToolTipsVisible(True)
        submenu_file = menu.addMenu("File")
        submenu_cleanup = menu.addMenu("Cleanup")
        # submenu_mark = menu.addMenu("Mark As")
        submenu_file.addAction(
            "Open 'job.star' As Text",
            lambda: _impl.open_relion_job_star(self._ui, get_job()),
        )
        submenu_file.addAction(
            "Open 'job_pipeline.star' As Text",
            lambda: _impl.open_relion_job_pipeline_star(self._ui, get_job()),
        )
        submenu_file.addAction(
            "Open Job Parameters",
            lambda: _impl.open_job_parameters(self._ui, get_job()),
        )
        submenu_file.addSeparator()
        submenu_file.addAction(
            "Copy Directory Path",
            lambda: self._ui.set_clipboard(text=str(path.parent)),
        )
        submenu_file.addAction(
            "Copy Directory Relative Path",
            lambda: self._ui.set_clipboard(text=str(item.id())),
        )
        action = submenu_cleanup.addAction(
            "Gentle Clean", lambda: _impl.gentle_clean_relion_job(self._ui, get_job())
        )
        action.setEnabled(status not in [NodeStatus.RUNNING, NodeStatus.SCHEDULED])
        action = submenu_cleanup.addAction(
            "Harsh Clean", lambda: _impl.harsh_clean_relion_job(self._ui, get_job())
        )
        action.setEnabled(status not in [NodeStatus.RUNNING, NodeStatus.SCHEDULED])
        # action = submenu_mark.addAction(
        #     "Mark As Finished", lambda: _impl.mark_as_finished(get_job())
        # )
        # action.setEnabled(status is not NodeStatus.SUCCEEDED)
        # action = submenu_mark.addAction(
        #     "Mark As Failed", lambda: _impl.mark_as_failed(get_job())
        # )
        # action.setEnabled(status is not NodeStatus.FAILED)
        menu.addSeparator()

        # Prepare next actions
        action_hints = _create_action_hint_menu(self._ui, path)
        if action_hints:
            action_hint_menu = menu.addMenu("Next Action ...")
            for action in action_hints:
                action.setParent(action_hint_menu)
                action_hint_menu.addAction(action)

        # Abort
        action = menu.addAction(
            "Abort", lambda: _ignore_cancel(_impl.abort_relion_job, self._ui, get_job())
        )
        action.setEnabled(status is NodeStatus.RUNNING)
        action.setToolTip("Notify the job to be aborted.")
        # Run now
        action = menu.addAction(
            "Run This Scheduled Job Now",
            lambda: execute_job(item.id(), cwd=self._relion_project_dir),
        )
        action.setToolTip(
            "Run this scheduled job immediately, regardless of whether all the parent\n"
            "jobs have finished or not."
        )
        action.setEnabled(status is NodeStatus.SCHEDULED)
        # Overwrite
        action = menu.addAction(
            "Overwrite ...", lambda: _impl.overwrite_relion_job(self._ui, get_job())
        )
        action.setToolTip(
            "Overwrite this job by re-running it with a new set of parameters."
        )
        # Clone
        action = menu.addAction(
            "Clone ...", lambda: _impl.clone_relion_job(self._ui, get_job())
        )
        action.setToolTip("Create a same type of job with a new set of parameters.")

        menu.addAction(
            "Set Alias ...",
            lambda: _ignore_cancel(_impl.set_job_alias, self._ui, get_job()),
        )
        menu.addSeparator()
        action = menu.addAction(
            "Trash", lambda: _ignore_cancel(_impl.trash_job, self._ui, get_job())
        )
        menu.addSeparator()
        action.setEnabled(status is not NodeStatus.RUNNING)
        action = menu.addAction("Set As Root Job", lambda: self.set_root_job(item._job))
        action.setEnabled(item._job is not self._root_job_info)
        action.setToolTip(
            "Set a job as the root of the flowchart.\n"
            "Only the descendants jobs of the root job will be shown in the\n"
            "flowchart. This operation is just a filtering and does not modify the\n"
            "underlying pipeline star file."
        )
        action = menu.addAction("Unset As Root Job", lambda: self.set_root_job(None))
        action.setToolTip("Unset the root job and show all jobs in the flowchart.")
        action.setEnabled(item._job is self._root_job_info)
        return menu


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

    def job_dir(self, relion_dir: Path) -> JobDirectory | None:
        """Return the job directory"""
        path = relion_dir / self._job.path
        if path.exists():
            return JobDirectory(relion_dir / self._job.path)


def _track_children(root: RelionJobInfo) -> set[Path]:
    all_paths = {root.path}
    for child in root.children:
        all_paths.add(child.node.path)
        all_paths.update(_track_children(child.node))
    return all_paths


def _create_action_hint_menu(ui: MainWindow, job_star_path: Path) -> list[QtW.QAction]:
    actions = []
    try:
        model_type = JobDirectory.from_job_star(job_star_path).himena_model_type()
        method = LocalReaderMethod(
            path=job_star_path,
            plugin="himena_relion.io.read_relion_job",
            output_model_type=model_type,
        )
        for attr, exe in ui.action_hint_registry.iter_executors(ui, model_type, method):
            action = QtW.QAction(attr.title)
            action.triggered.connect(exe)
            action.setToolTip(attr.tooltip)
            actions.append(action)
    except Exception as e:
        ui.show_notification(f"Failed to create action hint menu: {e}", title="Warning")
    return actions


def _ignore_cancel(func, *args, **kwargs):
    """Decorator to ignore Cancelled exception."""
    with suppress(Cancelled):
        return func(*args, **kwargs)
