from __future__ import annotations
from pathlib import Path
from typing import Iterable
import uuid
import warnings
from qtpy import QtGui, QtCore, QtWidgets as QtW

from himena.qt._qflowchart import QFlowChartView, TagItem
from himena.qt._qflowchart import QFlowChartNode, BaseNodeItem
from himena_relion import __version__
from himena_relion._utils import normalize_job_id
from himena_relion._pipeline import RelionDefaultPipeline, RelionJobInfo
from himena_relion.pipeline._gui_state import (
    _GUI_STATE_FILENAME,
    HimenaRelionGuiState,
    JobState,
    TagState,
    GroupState,
)
from himena_relion.pipeline._utils import (
    RelionJobNodeItem,
    RelionJobGroupNodeItem,
    split_job_info,
)


class QRelionPipelineFlowChartView(QFlowChartView):
    def __init__(self):
        self._scene = QtW.QGraphicsScene()
        super().__init__(self._scene)
        self._pipeline = RelionDefaultPipeline.empty()
        self._relion_project_dir: Path = Path.cwd()

        self._last_selection_highlight_rect = None
        self._dodge_distance = 64
        self._id_added = set()

        # groups of collapsed jobs
        self._groups: list[GroupState] = []
        self._groups_unsaved = False
        self._job_to_group: dict[Path, uuid.UUID] = {}
        self._group_items: dict[uuid.UUID, RelionJobGroupNodeItem] = {}

        # event connection
        self.item_right_clicked.connect(self._on_right_clicked)
        self.item_left_clicked.connect(self._update_selection_rect)

    def set_pipeline(self, pipeline: RelionDefaultPipeline) -> None:
        if not isinstance(pipeline, RelionDefaultPipeline):
            raise TypeError("Model value must be a RelionDefaultPipeline.")
        self._pipeline = pipeline
        if not self._groups_unsaved:
            if (groups := self._load_groups()) is not None:
                self._groups = groups
        self._rebuild()

    def _rebuild(self) -> None:
        """Rebuild all the nodes, keeping the positions of the existing nodes."""
        # If the flowchart has been dragged, item positions are different from default.
        old_positions = {
            node.item().id(): node.pos() for node in self._node_map.values()
        }
        default_pos = next(iter(old_positions.values()), QtCore.QPointF(0, 0))

        # NOTE: Adding only the new nodes to the existing flowchart usually puts them
        # in wrong places. All the nodes have to be added again from scratch.
        self.clear_items()
        self._id_added.clear()
        self._update_group_items()
        for info in self._pipeline._nodes:
            self._add_job_node_item(info)
        for node_id, node in list(self._node_map.items()):
            node.setPos(old_positions.get(node_id, default_pos))

    def read_gui_state(self, pipeline: RelionDefaultPipeline):
        project_dir = pipeline.project_dir
        try:
            gui_state = HimenaRelionGuiState.try_from_project_directory(project_dir)
            if gui_state is None:
                if project_dir.joinpath(_GUI_STATE_FILENAME).exists():
                    return  # failed to read the file. Keep the current state.
                gui_state = HimenaRelionGuiState()
            if not self._groups_unsaved and gui_state.groups != self._groups:
                self._groups = gui_state.groups
                self._rebuild()

            tags = [
                TagItem(name=tag.name, color=tag.color, id=tag.id)
                for tag in gui_state.tag_choices
            ]

            self.reset_tags(tags)

            for job_id, job_state in gui_state.jobs.items():
                my_tags = [tags[tag_index] for tag_index in job_state.tags]
                self.set_item_tags(Path(job_id), my_tags)
        except Exception as e:
            warnings.warn(
                f"Failed to read GUI state: {e}",
                RuntimeWarning,
                stacklevel=1,
            )

    def save_gui_state(self, pipeline: RelionDefaultPipeline):
        project_dir = pipeline.project_dir
        existing_tags = self.tags()
        tag_id_to_index = {tag.id: idx for idx, tag in enumerate(existing_tags)}
        try:
            # NOTE: other fields such as `jobs_opened` must not be lost.
            gui_state = HimenaRelionGuiState.from_project_directory(project_dir)
            # The jobs collapsed in groups are not in the flowchart. Keep their states.
            collapsed = {normalize_job_id(path) for path in self._job_to_group}
            jobs = {
                job_id: job_state
                for job_id, job_state in gui_state.jobs.items()
                if job_id in collapsed
            }
            for job_id, node in list(self._node_map.items()):
                if not isinstance(node.item(), RelionJobNodeItem):
                    continue
                tags: list[int] = []
                for tag in self.item_tags(job_id):
                    if (index := tag_id_to_index.get(tag.id)) is not None:
                        tags.append(index)
                if tags:
                    jobs[normalize_job_id(job_id)] = JobState(tags=tags)

            gui_state.jobs = jobs
            gui_state.tag_choices = [
                TagState(name=tag.name, color=tag.color.hex, id=tag.id)
                for tag in existing_tags
            ]
            gui_state.groups = list(self._groups)
            gui_state.version = __version__
            gui_state.dump_to_project_directory(project_dir)
            self._groups_unsaved = False
        except Exception as e:
            warnings.warn(
                f"Failed to save GUI state: {e}",
                RuntimeWarning,
                stacklevel=1,
            )

    ### Groups of collapsed jobs ###

    def groups(self) -> list[GroupState]:
        """List of the job groups."""
        return list(self._groups)

    def descendants(self, paths: Iterable[Path]) -> list[Path]:
        """All the downstream jobs of the given jobs, in the order of the pipeline."""
        infos = {info.path: info for info in self._pipeline._nodes}
        found = set[Path]()
        stack = [infos[path] for path in paths if path in infos]
        while stack:
            info = stack.pop()
            for child in info.children:
                if (path := child.node.path) not in found:
                    found.add(path)
                    stack.append(child.node)
        return [path for path in infos if path in found]

    def collapsible_children(self, item: BaseNodeItem) -> list[Path]:
        """The jobs that will be collapsed by `collapse_children`."""
        if isinstance(item, RelionJobGroupNodeItem):
            roots = [job.path for job in item.jobs]
        elif isinstance(item, RelionJobNodeItem):
            roots = [item.id()]
        else:
            return []
        return [path for path in self.descendants(roots) if path not in roots]

    def collapse_children(self, item: BaseNodeItem) -> RelionJobGroupNodeItem | None:
        """Collapse all the downstream jobs of the item into a group.

        If the item is a job, a new group is created. If the item is a group, the
        downstream jobs are added to the group.
        """
        if not (paths := self.collapsible_children(item)):
            return None
        new_ids = [normalize_job_id(path) for path in paths]
        if isinstance(item, RelionJobGroupNodeItem):
            if (group := self._group_by_id(item.group_id)) is None:
                return None
            new_group = group.model_copy(update={"jobs": group.jobs + new_ids})
        else:
            jobxxx, _ = split_job_info(item._job)
            new_group = GroupState(name=f"Downstream of {jobxxx}", jobs=new_ids)
        # a job cannot belong to multiple groups
        groups: list[GroupState] = []
        is_replaced = False
        for group in self._groups:
            if group.id == new_group.id:
                groups.append(new_group)
                is_replaced = True
            elif jobs := [job for job in group.jobs if Path(job) not in paths]:
                groups.append(group.model_copy(update={"jobs": jobs}))
        if not is_replaced:
            groups.append(new_group)
        self._set_groups(groups)
        if node := self._node_map.get(f"group:{new_group.id}"):
            node.setSelected(True)
            return node.item()
        return None

    def uncollapse(self, group_id: uuid.UUID) -> None:
        """Dissolve the group to show all the jobs in it."""
        self._set_groups([group for group in self._groups if group.id != group_id])

    def uncollapse_all(self) -> None:
        """Dissolve all the groups."""
        if self._groups:
            self._set_groups([])

    def rename_group(self, group_id: uuid.UUID, name: str) -> None:
        """Rename the group."""
        self._set_groups(
            [
                group.model_copy(update={"name": name})
                if group.id == group_id
                else group
                for group in self._groups
            ]
        )

    def display_item(self, path: Path) -> BaseNodeItem | None:
        """The item that displays the job (the group item if the job is collapsed)."""
        if node := self._node_map.get(path):
            return node.item()
        if (group_id := self._job_to_group.get(path)) is not None:
            return self._group_items.get(group_id)
        return None

    def center_on_item(self, item: BaseNodeItem, animate: bool = False):
        if item.id() not in self._node_map:
            # the job is collapsed in a group.
            item = self.display_item(item.id()) or item
        return super().center_on_item(item, animate)

    def _group_by_id(self, group_id: uuid.UUID) -> GroupState | None:
        for group in self._groups:
            if group.id == group_id:
                return group
        return None

    def _load_groups(self) -> list[GroupState] | None:
        """Load the groups from the GUI state file (None if failed to read)."""
        project_dir = self._pipeline.project_dir
        if gui_state := HimenaRelionGuiState.try_from_project_directory(project_dir):
            return gui_state.groups
        if project_dir.joinpath(_GUI_STATE_FILENAME).exists():
            return None
        return []

    def _set_groups(self, groups: list[GroupState]) -> None:
        self._groups = groups
        # If the GUI state cannot be saved (such as read-only projects), the groups
        # are kept only in this widget.
        self._groups_unsaved = True
        self._rebuild()
        self.read_gui_state(self._pipeline)  # restore the tags
        self.save_gui_state(self._pipeline)

    def _update_group_items(self) -> None:
        infos = {info.path: info for info in self._pipeline._nodes}
        self._job_to_group.clear()
        self._group_items.clear()
        for group in self._groups:
            jobs: list[RelionJobInfo] = []
            for job_id in group.jobs:
                path = Path(job_id)
                if path in infos and path not in self._job_to_group:
                    self._job_to_group[path] = group.id
                    jobs.append(infos[path])
            if jobs:
                self._group_items[group.id] = RelionJobGroupNodeItem(
                    group.id, group.name, jobs
                )

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

    def current_item(self) -> RelionJobNodeItem | None:
        """The selected job item (None if a group is selected)."""
        for qitem in self.scene().selectedItems():
            if isinstance(qitem, QFlowChartNode) and isinstance(
                item := qitem.item(), RelionJobNodeItem
            ):
                return item

    def _add_job_node_item(
        self,
        info: RelionJobInfo,
        ids_to_skip: set | None = None,
    ):
        if (group_id := self._job_to_group.get(info.path)) is not None:
            item = self._group_items[group_id]
            parent_infos = [p.node for job in item.jobs for p in job.parents]
        else:
            item = RelionJobNodeItem(info)
            parent_infos = [p.node for p in info.parents]
        item_id = item.id()
        if item_id in self._id_added:
            return self._node_map.get(item_id)
        if ids_to_skip is None:
            ids_to_skip = set()
        if item_id in ids_to_skip:
            return None
        ids_to_skip.add(item_id)  # recursion guard
        parents: list = []  # parent of incoming item
        for parent_info in parent_infos:
            parent_id = self._display_id(parent_info.path)
            if parent_id == item_id:
                continue  # connection inside a group
            if parent_id not in self._node_map:
                self._add_job_node_item(parent_info, ids_to_skip)
            if parent_id not in parents:
                parents.append(parent_id)
        qitem = self.add_child(item, parents=parents)
        self._id_added.add(item_id)
        if isinstance(item, RelionJobGroupNodeItem):
            pen = QtGui.QPen(QtCore.Qt.GlobalColor.black, 1.5)
            pen.setStyle(QtCore.Qt.PenStyle.DashLine)
            qitem.setPen(pen)
        return qitem

    def _display_id(self, path: Path):
        """The ID of the node that displays the job."""
        if (group_id := self._job_to_group.get(path)) is not None:
            return self._group_items[group_id].id()
        return path

    def _on_right_clicked(self, item: BaseNodeItem):
        if node := self._node_map.get(item.id()):
            node.setSelected(True)

    def mousePressEvent(self, event):
        self._update_selection_rect()
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self._update_selection_rect()
        return super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        self._update_selection_rect()
        return super().wheelEvent(event)

    def _update_selection_rect(self):
        if self._last_selection_highlight_rect:
            self.update(self._last_selection_highlight_rect.adjusted(-5, -5, 5, 5))
