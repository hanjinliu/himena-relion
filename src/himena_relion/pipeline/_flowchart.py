from __future__ import annotations
from pathlib import Path
import warnings
from qtpy import QtGui, QtCore, QtWidgets as QtW

from himena.qt._qflowchart import QFlowChartView, TagItem
from himena.qt._qflowchart import QFlowChartNode
from himena_relion._utils import normalize_job_id
from himena_relion._pipeline import RelionDefaultPipeline, RelionJobInfo
from himena_relion.pipeline._gui_state import HimenaRelionGuiState, JobState, TagState
from himena_relion.pipeline._utils import RelionJobNodeItem


class QRelionPipelineFlowChartView(QFlowChartView):
    def __init__(self):
        self._scene = QtW.QGraphicsScene()
        super().__init__(self._scene)
        self._pipeline = RelionDefaultPipeline.empty()
        self._relion_project_dir: Path = Path.cwd()

        self._last_selection_highlight_rect = None
        self._dodge_distance = 64
        self._id_added = set()

        # event connection
        self.item_right_clicked.connect(self._on_right_clicked)
        self.item_left_clicked.connect(self._update_selection_rect)

    def set_pipeline(self, pipeline: RelionDefaultPipeline) -> None:
        if not isinstance(pipeline, RelionDefaultPipeline):
            raise TypeError("Model value must be a RelionDefaultPipeline.")
        self._pipeline = pipeline

        old_positions = {
            node.item().id(): node.pos() for node in self._node_map.values()
        }
        # clear all
        self.clear_items()
        self._id_added.clear()

        # Parents for filtering the flowchart
        _allowed_parents = {node.path for node in pipeline._nodes}

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
        self.clear_items()
        self._id_added.clear()

        for info in pipeline._nodes:
            if info.path in old_positions:
                self._add_job_node_item(info, _allowed_parents)
        for new_item in self._node_map.values():
            if pos := old_positions.get(new_item.item().id()):
                new_item.setPos(pos)

    def read_gui_state(self, pipeline: RelionDefaultPipeline):
        project_dir = pipeline.project_dir
        try:
            gui_state = HimenaRelionGuiState.from_project_directory(project_dir)

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
        jobs = {}
        existing_tags = self.tags()
        tag_id_to_index = {tag.id: idx for idx, tag in enumerate(existing_tags)}
        try:
            for job_id in self._node_map.keys():
                tags = []
                for tag in self.item_tags(job_id):
                    if (index := tag_id_to_index.get(tag.id)) is not None:
                        tags.append(index)
                jobs[normalize_job_id(job_id)] = JobState(tags=tags)

            gui_state = HimenaRelionGuiState(
                jobs=jobs,
                tag_choices=[
                    TagState(name=tag.name, color=tag.color.hex, id=tag.id)
                    for tag in existing_tags
                ],
            )
            gui_state.dump_to_project_directory(project_dir)
        except Exception as e:
            warnings.warn(
                f"Failed to save GUI state: {e}",
                RuntimeWarning,
                stacklevel=1,
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

    def current_item(self):
        for qitem in self.scene().selectedItems():
            if isinstance(qitem, QFlowChartNode):
                return qitem.item()

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

    def _on_right_clicked(self, item: RelionJobNodeItem):
        if node := self._node_map.get(item.id()):
            node.setSelected(True)

    def mousePressEvent(self, event):
        self._update_selection_rect()
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self._update_selection_rect()
        return super().mouseMoveEvent(event)

    def _update_selection_rect(self):
        if self._last_selection_highlight_rect:
            self.update(self._last_selection_highlight_rect.adjusted(-5, -5, 5, 5))


def _track_children(root: RelionJobInfo) -> set[Path]:
    all_paths = {root.path}
    for child in root.children:
        all_paths.add(child.node.path)
        all_paths.update(_track_children(child.node))
    return all_paths
