from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
import warnings
from datetime import datetime
from qtpy import QtGui, QtCore, QtWidgets as QtW

from himena.qt import QColoredToolButton
from himena.qt.magicgui import ToggleButtons
from himena_relion._utils import normalize_job_id
from himena_relion._pipeline import RelionDefaultPipeline
from himena_relion.pipeline._gui_state import HimenaRelionGuiState
from himena_relion._utils import path_icon_svg
from ._utils import split_job_info, RelionJobNodeItem


class QRelionPipelineTableView(QtW.QWidget):
    item_left_pressed = QtCore.Signal(RelionJobNodeItem)
    item_right_pressed = QtCore.Signal(RelionJobNodeItem)
    item_left_clicked = QtCore.Signal(RelionJobNodeItem)
    item_right_clicked = QtCore.Signal(RelionJobNodeItem)
    item_left_double_clicked = QtCore.Signal(RelionJobNodeItem)

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._header_widget = QtW.QWidget()
        self._table_view = _QRelionPipelineTableView(self)
        layout.addWidget(self._header_widget)
        layout.addWidget(self._table_view)

        # prepare header
        self._sort_by_widget_mgui = ToggleButtons(["Job ID", "Time"])
        self._sort_by_widget_mgui.changed.connect(self._on_sort_by_changed)
        self._sort_ascending_btn = QColoredToolButton(
            self._switch_sort_order,
            path_icon_svg("switch_up_down"),
        )
        self._sort_ascending_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._sort_ascending_btn.setToolTip("Switch sort order")
        self._sort_is_ascending = True

        header_layout = QtW.QHBoxLayout(self._header_widget)
        header_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(QtW.QLabel("Sort by:", self._header_widget))
        header_layout.addWidget(self._sort_by_widget_mgui.native)
        header_layout.addWidget(self._sort_ascending_btn)

        # connect signals
        self._table_view.item_left_pressed.connect(self.item_left_pressed)
        self._table_view.item_right_pressed.connect(self.item_right_pressed)
        self._table_view.item_left_clicked.connect(self.item_left_clicked)
        self._table_view.item_right_clicked.connect(self.item_right_clicked)
        self._table_view.item_left_double_clicked.connect(self.item_left_double_clicked)

    def set_pipeline(self, pipeline: RelionDefaultPipeline) -> None:
        if not isinstance(pipeline, RelionDefaultPipeline):
            raise TypeError("Model value must be a RelionDefaultPipeline.")
        self._table_view._model = QRelionPipelineTableViewModel(
            self,
            pipeline,
            HimenaRelionGuiState.from_project_directory(pipeline.project_dir),
        )
        self._table_view.setModel(self._table_view._model)
        self._table_view.setColumnWidth(0, 60)
        self._table_view.setColumnWidth(1, 180)

    def item_from_index(self, index: QtCore.QModelIndex) -> RelionJobNodeItem | None:
        if not index.isValid():
            return None
        return self._table_view._model.relion_job_node_item(index.row())

    def current_item(self) -> RelionJobNodeItem | None:
        index = self._table_view.currentIndex()
        return self.item_from_index(index)

    def read_gui_state(self, pipeline: RelionDefaultPipeline):
        project_dir = pipeline.project_dir
        try:
            gui_state = HimenaRelionGuiState.from_project_directory(project_dir)

            self._table_view._model.update_gui_state(gui_state)
        except Exception as e:
            warnings.warn(
                f"Failed to read GUI state: {e}",
                RuntimeWarning,
                stacklevel=1,
            )

    def center_on_item(self, path: Path):
        _model = self._table_view._model
        for row in range(_model.rowCount()):
            if _model.relion_job_node_item(row).id() == path:
                index = _model.index(row, 0)
                self._table_view.scrollTo(
                    index, QtW.QAbstractItemView.ScrollHint.PositionAtCenter
                )
                self._table_view.setCurrentIndex(index)

    def _on_sort_by_changed(self, value: str):
        if self._table_view._model is None:
            return
        if value == "Job ID":
            new_proxy = IdentityProxy(self._table_view._model._pipeline)
        elif value == "Time":
            new_proxy = SortByTimeProxy(self._table_view._model._pipeline)
        else:  # pragma: no cover
            raise ValueError("Invalid sort index")
        self._table_view._model.set_proxy(new_proxy, ascending=self._sort_is_ascending)

    def _switch_sort_order(self):
        if self._table_view._model is None:
            return
        self._sort_is_ascending = not self._sort_is_ascending
        proxy = self._table_view._model._proxy
        self._table_view._model.set_proxy(proxy, ascending=self._sort_is_ascending)


class _QRelionPipelineTableView(QtW.QTableView):
    item_left_pressed = QtCore.Signal(RelionJobNodeItem)
    item_right_pressed = QtCore.Signal(RelionJobNodeItem)
    item_left_clicked = QtCore.Signal(RelionJobNodeItem)
    item_right_clicked = QtCore.Signal(RelionJobNodeItem)
    item_left_double_clicked = QtCore.Signal(RelionJobNodeItem)

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._model: QRelionPipelineTableViewModel | None = None
        self.viewport().setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        self.setSelectionBehavior(QtW.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QtW.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setFixedHeight(20)
        self.verticalHeader().setDefaultSectionSize(22)
        self.setVerticalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.doubleClicked.connect(self._double_clicked)
        self._drag_start_pos = QtCore.QPoint()

    def _double_clicked(self, index: QtCore.QModelIndex):
        if not index.isValid():
            return
        item = self._model.relion_job_node_item(index.row())
        self.item_left_double_clicked.emit(item)

    def mousePressEvent(self, e):
        self._drag_start_pos = e.pos()
        index = self.indexAt(self._drag_start_pos)
        if index.isValid():
            item = self._model.relion_job_node_item(index.row())
            if e.button() == QtCore.Qt.MouseButton.LeftButton:
                self.item_left_pressed.emit(item)
            elif e.button() == QtCore.Qt.MouseButton.RightButton:
                self.item_right_pressed.emit(item)
        return super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        index = self.indexAt(self._drag_start_pos)
        if index.isValid() and (e.pos() - self._drag_start_pos).manhattanLength() < 5:
            item = self._model.relion_job_node_item(index.row())
            if e.button() == QtCore.Qt.MouseButton.LeftButton:
                self.item_left_clicked.emit(item)
            elif e.button() == QtCore.Qt.MouseButton.RightButton:
                self.item_right_clicked.emit(item)
        self._drag_start_pos = QtCore.QPoint()
        return super().mouseReleaseEvent(e)


class QRelionPipelineTableViewModel(QtCore.QAbstractTableModel):
    def __init__(
        self,
        parent: QtW.QWidget,
        pipeline: RelionDefaultPipeline,
        gui_state: HimenaRelionGuiState,
    ):
        super().__init__(parent)
        self._pipeline = pipeline
        self._gui_state = gui_state
        self._proxy = IdentityProxy(pipeline)
        self._is_ascending = True

    def relion_job_node_item(self, index: int) -> RelionJobNodeItem:
        if not self._is_ascending:
            # If descending, map the index to the end of the list
            index = self._proxy.count() - 1 - index
        job_info = self._pipeline[self._proxy.map(index)]
        return RelionJobNodeItem(job_info)

    def set_proxy(self, proxy: TableProxy, ascending: bool = True):
        self.beginResetModel()
        self._proxy = proxy
        self._is_ascending = ascending
        self.endResetModel()

    def rowCount(self, parent: QtCore.QModelIndex = None) -> int:
        return self._proxy.count()

    def columnCount(self, parent: QtCore.QModelIndex = None):
        return 3

    def data(
        self,
        index: QtCore.QModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid():
            return None
        job_info = self.relion_job_node_item(index.row())._job
        column = index.column()
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if column == 0:  # job012
                return split_job_info(job_info)[0]
            elif column == 1:
                title = split_job_info(job_info)[1]
                if job_info.alias:
                    return f"{job_info.alias} ({title})"
                return title
            elif column == 2:
                if job_state := self._gui_state.jobs.get(
                    normalize_job_id(job_info.path)
                ):
                    tags = self._gui_state.tag_choices
                    return ", ".join(
                        f"#{tags[tag_index].name}" for tag_index in job_state.tags
                    )
                return ""
        elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
            try:
                stat = job_info.path.resolve().stat()
            except Exception:
                return "<Job directory does not exist>"
            job, title = split_job_info(job_info)
            if job_info.alias:
                first_line = f"{job}: {job_info.alias} ({title})"
            else:
                first_line = f"{job}: {title}"
            dt = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            return (
                f"{first_line}\n"
                f"Status: {job_info.status.value.capitalize()}\n"
                f"Last modified: {dt}"
            )
        elif role == QtCore.Qt.ItemDataRole.DecorationRole and column == 0:
            relion_job_node_item = self.relion_job_node_item(index.row())
            qcolor = QtGui.QColor.fromRgbF(*relion_job_node_item.color().rgba)
            pixmap = QtGui.QPixmap(16, 16)
            pixmap.fill(qcolor)
            return QtGui.QIcon(pixmap)
        return None

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ):
        if (
            role == QtCore.Qt.ItemDataRole.DisplayRole
            and orientation == QtCore.Qt.Orientation.Horizontal
            and 0 <= section < 3
        ):
            return ["Job", "Title", "Tags"][section]
        return None

    def update_gui_state(self, gui_state: HimenaRelionGuiState):
        self._gui_state = gui_state
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1),
            [QtCore.Qt.ItemDataRole.DisplayRole],
        )


class TableProxy(ABC):
    @abstractmethod
    def map(self, index: int) -> int:
        """Map the index from the top of the table to the index in the pipeline."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of items after the proxy is applied."""


class IdentityProxy(TableProxy):
    def __init__(self, pipeline: RelionDefaultPipeline):
        self._count = len(pipeline)

    def map(self, index: int) -> int:
        return index

    def count(self) -> int:
        return self._count


class SortByTimeProxy(TableProxy):
    def __init__(self, pipeline: RelionDefaultPipeline):
        self._sorted_indices = sorted(
            range(len(pipeline)),
            key=lambda i: pipeline[i].path.stat().st_mtime,
        )

    def map(self, index: int) -> int:
        return self._sorted_indices[index]

    def count(self) -> int:
        return len(self._sorted_indices)
