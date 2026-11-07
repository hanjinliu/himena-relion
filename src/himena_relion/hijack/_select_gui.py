"""Qt GUI for the interactive class selection, shown in the Results tab."""

from __future__ import annotations

from enum import Enum
import logging
from pathlib import Path
import traceback

import numpy as np
from numpy.typing import NDArray
from qtpy import QtCore, QtGui, QtWidgets as QtW
from superqt.utils import GeneratorWorker, thread_worker
from himena.qt.magicgui import ToggleButtons
from himena_relion._impl_objects import start_worker
from himena_relion._job_dir import JobDirectory
from himena_relion._widgets._job_widgets import JobWidgetBase
from himena_relion.consts import FileNames
from himena_relion.hijack._base import (
    append_run_err,
    append_run_out,
    finish_job,
    running_hijacker,
    uses_himena_impl,
)
from himena_relion.hijack.select_interactive import (
    ClassSelectionInput,
    SelectionParams,
    read_backup_selection,
    recenter_image,
    write_selection,
)

_LOGGER = logging.getLogger(__name__)
_CLASS_INDEX_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1
_SELECTED_COLOR = QtGui.QColor("#ff3b30")
_TEXT_LINE_HEIGHT = 14
_HOVER_FRAME_WIDTH = 3


class SortBy(Enum):
    CLASS_NUMBER = "Class number"
    PARTICLES = "Particle number"
    RESOLUTION = "Resolution"


class Plane(Enum):
    XY = "XY"
    XZ = "XZ"
    YZ = "YZ"


class Projection(Enum):
    MEAN = "Mean"
    MAX = "Max"
    SLICE = "Central slice"


class ClassImages:
    """Images to display for a class (projections for 3D maps)."""

    def __init__(self, img: NDArray[np.floating] | None, recenter: bool = False):
        self._images: dict[tuple[Plane, Projection] | None, NDArray[np.float32]] = {}
        if img is None:
            return
        if img.ndim == 2:
            self._images[None] = recenter_image(img) if recenter else img
        else:
            for axis, plane in enumerate(Plane):
                self._images[(plane, Projection.MEAN)] = img.mean(axis=axis)
                self._images[(plane, Projection.MAX)] = img.max(axis=axis)
                self._images[(plane, Projection.SLICE)] = np.take(
                    img, img.shape[axis] // 2, axis=axis
                )

    def get(self, plane: Plane, projection: Projection) -> NDArray[np.float32] | None:
        if None in self._images:
            return self._images[None]
        return self._images.get((plane, projection))


def _to_qimage(img: NDArray[np.floating] | None) -> QtGui.QImage:
    if img is None:
        out = QtGui.QImage(16, 16, QtGui.QImage.Format.Format_Grayscale8)
        out.fill(QtGui.QColor(40, 40, 40))
        return out
    img = np.flipud(np.asarray(img, dtype=np.float32))  # y axis upward
    min0, max0 = float(img.min()), float(img.max())
    if max0 > min0:
        normed = (img - min0) / (max0 - min0) * 255
    else:
        normed = np.zeros_like(img)
    arr = np.ascontiguousarray(normed.astype(np.uint8))
    h, w = arr.shape
    qimg = QtGui.QImage(arr.data, w, h, w, QtGui.QImage.Format.Format_Grayscale8)
    return qimg.copy()  # detach from the numpy buffer


class QClassListModel(QtCore.QAbstractListModel):
    """List model of classes, shown in the order of `order`."""

    def __init__(self, labels: list[str], tooltips: list[str], parent=None):
        super().__init__(parent)
        self._labels = labels
        self._tooltips = tooltips
        self._qimages: list[QtGui.QImage] = []
        self._order = np.arange(len(labels))

    def rowCount(self, parent=QtCore.QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._order)

    def data(self, index: QtCore.QModelIndex, role: int = 0):
        if not index.isValid():
            return None
        icls = int(self._order[index.row()])
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._labels[icls]
        elif role == QtCore.Qt.ItemDataRole.DecorationRole:
            if icls < len(self._qimages):
                return self._qimages[icls]
        elif role == QtCore.Qt.ItemDataRole.ToolTipRole:
            return self._tooltips[icls]
        elif role == _CLASS_INDEX_ROLE:
            return icls
        return None

    def order(self) -> NDArray[np.intp]:
        return self._order

    def set_order(self, order: NDArray[np.intp]):
        self.beginResetModel()
        self._order = np.asarray(order)
        self.endResetModel()

    def set_images(self, qimages: list[QtGui.QImage]):
        self._qimages = qimages
        if len(self._order) > 0:
            self.dataChanged.emit(self.index(0), self.index(len(self._order) - 1))


class QClassItemDelegate(QtW.QStyledItemDelegate):
    """Draw a class image with a frame (red if selected) and two lines of text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image_size = 128

    def image_size(self) -> int:
        return self._image_size

    def set_image_size(self, size: int):
        self._image_size = size

    def sizeHint(self, option, index) -> QtCore.QSize:
        s = self._image_size
        return QtCore.QSize(s + 8, s + 10 + 2 * _TEXT_LINE_HEIGHT)

    def paint(self, painter: QtGui.QPainter, option, index: QtCore.QModelIndex):
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        rect: QtCore.QRect = option.rect
        s = self._image_size
        img_rect = QtCore.QRect(rect.x() + 4, rect.y() + 4, s, s)
        is_selected = bool(option.state & QtW.QStyle.StateFlag.State_Selected)
        qimage = index.data(QtCore.Qt.ItemDataRole.DecorationRole)
        if isinstance(qimage, QtGui.QImage):
            painter.drawImage(img_rect, qimage)
        if is_selected:
            painter.setPen(QtGui.QPen(_SELECTED_COLOR, 4))
            painter.drawRect(img_rect.adjusted(1, 1, -1, -1))
        else:
            # dim unselected classes a bit
            painter.fillRect(img_rect, QtGui.QColor(0, 0, 0, 60))
            painter.setPen(QtGui.QPen(QtGui.QColor(128, 128, 128, 160), 1))
            painter.drawRect(img_rect)
        if option.state & QtW.QStyle.StateFlag.State_MouseOver:
            # drawn in the margin around the image, so that it does not hide the
            # red frame of the selected class
            pen = QtGui.QPen(option.palette.highlight().color(), _HOVER_FRAME_WIDTH)
            pen.setJoinStyle(QtCore.Qt.PenJoinStyle.MiterJoin)
            painter.setPen(pen)
            half = _HOVER_FRAME_WIDTH // 2
            painter.drawRect(rect.adjusted(half, half, -half - 1, -half - 1))
        text_rect = QtCore.QRect(
            rect.x(), img_rect.bottom() + 3, rect.width(), 2 * _TEXT_LINE_HEIGHT
        )
        font = painter.font()
        font.setPointSizeF(max(font.pointSizeF() - 1, 7))
        painter.setFont(font)
        color = _SELECTED_COLOR if is_selected else option.palette.text().color()
        painter.setPen(color)
        painter.drawText(
            text_rect,
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop,
            str(index.data(QtCore.Qt.ItemDataRole.DisplayRole)),
        )
        painter.restore()


class QClassListView(QtW.QListView):
    """Grid of classes. Click or drag to toggle selection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QtW.QListView.ViewMode.IconMode)
        self.setFlow(QtW.QListView.Flow.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QtW.QListView.ResizeMode.Adjust)
        self.setMovement(QtW.QListView.Movement.Static)
        self.setUniformItemSizes(True)
        self.setSpacing(2)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.MultiSelection)
        self.setMouseTracking(True)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.setVerticalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        # pointing hand only on the class items, not on the empty area
        if self.indexAt(e.pos()).isValid():
            self.viewport().setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        else:
            self.viewport().unsetCursor()
        return super().mouseMoveEvent(e)

    def leaveEvent(self, e: QtCore.QEvent):
        self.viewport().unsetCursor()
        return super().leaveEvent(e)


class QClassSelector(QtW.QWidget):
    """Panel for selecting 2D or 3D classes."""

    save_requested = QtCore.Signal()

    def __init__(
        self,
        source: ClassSelectionInput,
        class_images: list[ClassImages],
        *,
        initial: NDArray[np.bool_] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._source = source
        self._counts = source.particle_counts()
        self._resolutions = source.resolutions()
        self._distributions = source.class_distributions()
        self._num_classes = source.num_classes
        self._selected = np.zeros(self._num_classes, dtype=bool)
        self._is_3d = source.is_3d()
        self._class_images = class_images

        labels: list[str] = []
        tooltips: list[str] = []
        for num, count, res, dist in zip(
            source.class_numbers, self._counts, self._resolutions, self._distributions
        ):
            labels.append(f"#{num}  {dist * 100:.1f}%\n{res:.1f} Å  ({count})")
            tooltips.append(
                f"Class {num}\nParticles: {count}\nDistribution: {dist * 100:.2f}%\n"
                f"Resolution: {res:.2f} Å"
            )

        # widgets
        self._model = QClassListModel(labels, tooltips, self)
        self._delegate = QClassItemDelegate(self)
        self._view = QClassListView(self)
        self._view.setModel(self._model)
        self._view.setItemDelegate(self._delegate)

        self._sort_by = QtW.QComboBox(self)
        self._sort_by.addItems([s.value for s in SortBy])
        self._sort_by.setCurrentText(SortBy.CLASS_NUMBER.value)
        self._plane_mgui = ToggleButtons(value=Plane.XY, choices=Plane)
        self._projection_mgui = ToggleButtons(value=Projection.MEAN, choices=Projection)
        self._size_slider = QtW.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self._size_slider.setRange(48, 400)
        self._size_slider.setValue(self._delegate.image_size())
        self._size_slider.setMaximumWidth(140)
        self._summary = QtW.QLabel(self)
        self._input_label = QtW.QLabel(f"Input: <b>{source.fn_model}</b>", self)
        self._input_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._save_btn = QtW.QPushButton("Save selection", self)
        self._save_btn.setToolTip(
            "Save the selected classes and their particles, and finish this job."
        )
        self._save_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        select_all_btn = QtW.QPushButton("All", self)
        select_all_btn.setToolTip("Select all classes (Ctrl+A)")
        clear_btn = QtW.QPushButton("Clear", self)
        clear_btn.setToolTip("Deselect all classes")
        invert_btn = QtW.QPushButton("Invert", self)
        invert_btn.setToolTip("Invert the selection (Ctrl+I)")
        for btn in [select_all_btn, clear_btn, invert_btn]:
            btn.setMaximumWidth(64)
            btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        # layout
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self._input_label)
        top = QtW.QHBoxLayout()
        top.addWidget(QtW.QLabel("Sort by:"))
        top.addWidget(self._sort_by)
        top.addWidget(QtW.QLabel("Size:"))
        top.addWidget(self._size_slider)
        top.addStretch()
        layout.addLayout(top)
        view_options = QtW.QHBoxLayout()
        view_options.addWidget(QtW.QLabel("Plane:"))
        view_options.addWidget(self._plane_mgui.native)
        view_options.addWidget(QtW.QLabel("Projection:"))
        view_options.addWidget(self._projection_mgui.native)
        view_options.addStretch()
        self._view_options = QtW.QWidget(self)
        self._view_options.setLayout(view_options)
        view_options.setContentsMargins(0, 0, 0, 0)
        self._view_options.setVisible(self._is_3d)
        layout.addWidget(self._view_options)
        layout.addWidget(self._view, stretch=1)
        hint = QtW.QLabel(
            "Click or drag to toggle selection. Right-click for more options.", self
        )
        hint.setStyleSheet("color: gray;")
        layout.addWidget(hint)
        bottom = QtW.QHBoxLayout()
        bottom.addWidget(select_all_btn)
        bottom.addWidget(clear_btn)
        bottom.addWidget(invert_btn)
        bottom.addStretch()
        bottom.addWidget(self._save_btn)
        layout.addLayout(bottom)
        layout.addWidget(self._summary)

        # connections
        self._view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._view.customContextMenuRequested.connect(self._show_context_menu)
        self._sort_by.currentTextChanged.connect(self._update_order)
        self._plane_mgui.changed.connect(self._update_images)
        self._projection_mgui.changed.connect(self._update_images)
        self._size_slider.valueChanged.connect(self._set_image_size)
        self._save_btn.clicked.connect(self.save_requested.emit)
        select_all_btn.clicked.connect(self.select_all)
        clear_btn.clicked.connect(self.clear_selection)
        invert_btn.clicked.connect(self.invert_selection)
        for key, slot in [
            (QtGui.QKeySequence.StandardKey.SelectAll, self.select_all),
            ("Ctrl+I", self.invert_selection),
        ]:
            shortcut = QtGui.QShortcut(QtGui.QKeySequence(key), self)
            shortcut.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(slot)

        self._update_images()
        self._update_order()
        if initial is not None:
            self.set_selection(initial)
        self._update_summary()

    def selection(self) -> NDArray[np.bool_]:
        """Boolean array of selected classes, in the class order."""
        return self._selected.copy()

    def set_selection(self, selected: NDArray[np.bool_]):
        selected = np.asarray(selected, dtype=bool)
        if selected.shape != (self._num_classes,):
            raise ValueError("Selection shape mismatch.")
        self._selected = selected.copy()
        self._apply_selection_to_view()

    def select_all(self):
        self.set_selection(np.ones(self._num_classes, dtype=bool))

    def clear_selection(self):
        self.set_selection(np.zeros(self._num_classes, dtype=bool))

    def invert_selection(self):
        self.set_selection(~self._selected)

    def sort_by(self, by: SortBy | str):
        self._sort_by.setCurrentText(SortBy(by).value)

    def display_order(self) -> NDArray[np.intp]:
        """Class indices (0-based) in the display order."""
        return self._model.order().copy()

    def _update_order(self):
        # resetting the model clears the selection in the view
        selected = self._selected.copy()
        match SortBy(self._sort_by.currentText()):
            case SortBy.CLASS_NUMBER:
                order = np.arange(self._num_classes)
            case SortBy.PARTICLES:
                order = np.argsort(-self._counts, kind="stable")
            case SortBy.RESOLUTION:
                res = np.nan_to_num(self._resolutions, nan=np.inf)
                order = np.argsort(res, kind="stable")
        self._model.set_order(order)
        self._selected = selected
        self._apply_selection_to_view()

    def _update_images(self):
        plane = Plane(self._plane_mgui.value)
        projection = Projection(self._projection_mgui.value)
        qimages = [_to_qimage(ci.get(plane, projection)) for ci in self._class_images]
        self._model.set_images(qimages)

    def _set_image_size(self, size: int):
        self._delegate.set_image_size(size)
        self._model.layoutAboutToBeChanged.emit()
        self._model.layoutChanged.emit()
        self._view.doItemsLayout()

    def _apply_selection_to_view(self):
        sel_model = self._view.selectionModel()
        selection = QtCore.QItemSelection()
        for row, icls in enumerate(self._model.order()):
            if self._selected[icls]:
                index = self._model.index(row)
                selection.select(index, index)
        sel_model.blockSignals(True)
        try:
            sel_model.select(
                selection, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
            )
        finally:
            sel_model.blockSignals(False)
        self._view.viewport().update()
        self._update_summary()

    def _on_selection_changed(self, *_):
        selected = np.zeros(self._num_classes, dtype=bool)
        for index in self._view.selectionModel().selectedIndexes():
            selected[int(index.data(_CLASS_INDEX_ROLE))] = True
        self._selected = selected
        self._update_summary()

    def _update_summary(self):
        nsel = int(self._selected.sum())
        nparts = int(self._counts[self._selected].sum())
        ntotal = max(int(self._source.num_particles), 1)
        self._summary.setText(
            f"Selected <b>{nsel}</b>/{self._num_classes} classes, "
            f"<b>{nparts:,}</b>/{ntotal:,} particles ({nparts / ntotal:.1%})"
        )

    def _show_context_menu(self, pos: QtCore.QPoint):
        index = self._view.indexAt(pos)
        menu = QtW.QMenu(self)
        menu.addAction("Select all", self.select_all)
        menu.addAction("Clear selection", self.clear_selection)
        menu.addAction("Invert selection", self.invert_selection)
        if index.isValid():
            row = index.row()
            menu.addSeparator()
            menu.addAction(
                "Select all classes above", lambda: self._select_range(0, row + 1)
            )
            menu.addAction(
                "Select all classes below",
                lambda: self._select_range(row, self._model.rowCount()),
            )
        menu.exec(self._view.viewport().mapToGlobal(pos))

    def _select_range(self, start: int, stop: int):
        selected = self._selected.copy()
        selected[self._model.order()[start:stop]] = True
        self.set_selection(selected)


class QClassSelectionJobWidget(QtW.QWidget, JobWidgetBase):
    """Results tab of a running Select job that uses the himena-relion GUI.

    Classes are loaded in a worker thread. Saving the selection writes the outputs and
    marks the job as finished in the main thread.
    """

    job_finished = QtCore.Signal()

    def __init__(self, job_dir: JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        self._params: SelectionParams | None = None
        self._source: ClassSelectionInput | None = None
        self._selector: QClassSelector | None = None
        self._worker: GeneratorWorker | None = None
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self._message = QtW.QLabel("Loading classes ...", self)
        self._message.setWordWrap(True)
        self._message.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self._message)
        self._layout = layout

    def selector(self) -> QClassSelector | None:
        return self._selector

    def initialize(self, job_dir: JobDirectory):
        self._job_dir = job_dir
        if self._selector is not None or self._worker is not None:
            return  # already loaded; keep the current selection
        self._worker = self._load(job_dir)
        self._worker.yielded.connect(self._on_yielded)
        self._worker.finished.connect(self._on_worker_finished)
        start_worker(self._worker)

    def on_job_updated(self, job_dir: JobDirectory, fp: Path):
        if (
            Path(fp).name == FileNames.ABORT_NOW
            and job_dir.path.joinpath(FileNames.ABORT_NOW).exists()
            and uses_himena_impl(job_dir)
            and running_hijacker(job_dir) is None
        ):
            # Aborted from outside of himena-relion (e.g. RELION GUI). No process
            # can respond to it, so finish the job here.
            finish_job(job_dir, "Aborted")
            self.job_finished.emit()

    def save(self) -> bool:
        """Save the selection and finish the job."""
        if self._selector is None or self._source is None or self._params is None:
            return False
        selected = self._selector.selection()
        if not selected.any():
            QtW.QMessageBox.warning(
                self, "No selection", "No classes selected. Please select classes."
            )
            return False
        params = self._params
        try:
            result = write_selection(
                self._job_dir,
                self._source,
                selected,
                write_class_averages=params.write_class_averages,
                do_recenter=params.do_recenter,
                nr_regroups=params.nr_regroups,
                log=lambda msg: append_run_out(self._job_dir, msg),
            )
            finish_job(self._job_dir, "Succeeded")
        except Exception as e:
            _LOGGER.warning("Failed to save the selection", exc_info=True)
            append_run_err(self._job_dir, traceback.format_exc())
            QtW.QMessageBox.critical(self, "Failed to save", f"{type(e).__name__}: {e}")
            return False
        self._selector.setEnabled(False)
        self._message.setText(result.message())
        self._message.setVisible(True)
        self.job_finished.emit()
        return True

    def closeEvent(self, a0):
        self.window_closed_callback()
        return super().closeEvent(a0)

    def window_closed_callback(self):
        if self._worker is not None:
            self._worker.quit()
            self._worker = None

    @thread_worker
    def _load(self, job_dir: JobDirectory):
        try:
            params = SelectionParams.from_job_dir(job_dir)
            source = ClassSelectionInput.from_fn_model(
                params.fn_model, job_dir.relion_project_dir
            )
            images = [
                ClassImages(img, recenter=params.do_recenter)
                for img in source.iter_class_images()
            ]
            initial = read_backup_selection(job_dir, source.num_classes)
        except Exception as e:
            _LOGGER.warning("Failed to load the classes", exc_info=True)
            yield self._on_load_failed, (e, traceback.format_exc())
            return
        yield self._on_loaded, (params, source, images, initial)

    def _on_yielded(self, yielded):
        if yielded is not None:
            fn, args = yielded
            fn(args)

    def _on_worker_finished(self):
        self._worker = None

    def _on_loaded(self, value):
        params, source, images, initial = value
        self._params = params
        self._source = source
        self._selector = QClassSelector(source, images, initial=initial, parent=self)
        self._selector.save_requested.connect(self.save)
        self._layout.addWidget(self._selector, stretch=1)
        self._message.setVisible(False)

    def _on_load_failed(self, value: tuple[Exception, str]):
        exc, tb = value
        append_run_err(self._job_dir, tb)
        self._message.setText(
            f"<b>Failed to load the classes.</b><br>{type(exc).__name__}: {exc}<br><br>"
            "Abort this job and check the input (see run.err for details)."
        )
