from __future__ import annotations

import logging
from pathlib import Path

from qtpy import QtCore, QtGui, QtWidgets as QtW
from himena.widgets import current_instance
from himena_relion import _job_dir
from himena_relion._image_readers import ArrayFilteredView
from himena_relion._job_class import _JOB_DIR_ARGS_NAME
from himena_relion._widgets import (
    Q2DFilterWidget,
    Q2DViewer,
    QMicrographListWidget,
    spacer_widget,
)
from himena_relion._widgets._misc import QTableModel
from himena_relion._widgets._shared.resizer import QResizer
from himena_relion.consts import FileNames, RelionJobState
from ._impl import (
    OUTPUT_STAR,
    TomogramEntry,
    TomogramSet,
    last_selection,
    save_selection,
)

_LOGGER = logging.getLogger(__name__)
TOMO_VIEW_MIN_HEIGHT = 480
TOMO_VIEW_MAX_HEIGHT = 520
_CHECKED = QtCore.Qt.CheckState.Checked
_UNCHECKED = QtCore.Qt.CheckState.Unchecked
# files that change the state of the job or the saved selection
_FILES_TO_REFRESH = (
    FileNames.EXIT_SUCCESS,
    FileNames.EXIT_FAILURE,
    FileNames.EXIT_ABORTED,
    FileNames.ABORT_NOW,
    OUTPUT_STAR,
    "job.star",
)


class QCheckableTableModel(QTableModel):
    """Table model whose first column is checkable."""

    def __init__(self, data, columns, parent=None):
        super().__init__(data, columns, parent)
        self._checked: list[bool] = []
        self._checkable = True

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
        flags = super().flags(index)
        if index.isValid() and index.column() == 0 and self._checkable:
            flags |= QtCore.Qt.ItemFlag.ItemIsUserCheckable
        return flags

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if role == QtCore.Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            return _CHECKED if self._checked[index.row()] else _UNCHECKED
        return super().data(index, role)

    def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole) -> bool:
        if (
            role == QtCore.Qt.ItemDataRole.CheckStateRole
            and index.column() == 0
            and self._checkable
        ):
            self.set_checked_at(index.row(), _is_checked(value))
            return True
        return False

    def set_checked_at(self, row: int, checked: bool):
        self._checked[row] = checked
        index = self.index(row, 0)
        self.dataChanged.emit(index, index, [QtCore.Qt.ItemDataRole.CheckStateRole])

    def set_all_checked(self, checked: list[bool]):
        self._checked = list(checked)
        if self.rowCount() > 0:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(self.rowCount() - 1, 0),
                [QtCore.Qt.ItemDataRole.CheckStateRole],
            )


def _is_checked(value) -> bool:
    if isinstance(value, QtCore.Qt.CheckState):
        return value == _CHECKED
    return int(value) == 2  # Qt.CheckState.Checked


class QTomogramCheckList(QMicrographListWidget):
    """List of tomograms with check boxes. Space key toggles the current tomogram."""

    checked_changed = QtCore.Signal()

    def __init__(self, columns: list[str]):
        super().__init__(columns)
        old_model = self._model
        self._model = QCheckableTableModel([], list(columns), self)
        self.setModel(self._model)
        old_model.deleteLater()
        # setModel creates a new selection model
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._model.dataChanged.connect(self.checked_changed)

    def set_tomograms(self, rows: list[tuple[str, ...]], checked: list[bool]):
        self._model._checked = list(checked)
        self.set_choices(rows)
        self.checked_changed.emit()

    def set_checked(self, checked: list[bool]):
        self._model.set_all_checked(checked)

    def checked(self) -> list[bool]:
        return list(self._model._checked)

    def selection(self) -> dict[str, bool]:
        """Selection as {tomo_name: checked}."""
        return {row[0]: c for row, c in zip(self._model._data, self._model._checked)}

    def is_checkable(self) -> bool:
        return self._model._checkable

    def set_checkable(self, checkable: bool):
        self._model._checkable = checkable
        self.viewport().update()

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if (
            e.key() in (QtCore.Qt.Key.Key_Space, QtCore.Qt.Key.Key_Select)
            and self.is_checkable()
            and 0 <= (row := self.currentIndex().row()) < self.rowCount()
        ):
            self._model.set_checked_at(row, not self._model._checked[row])
            return
        return super().keyPressEvent(e)


class QSelectTomogramsViewer(QtW.QWidget):
    """Widget to check the tomograms to keep while the job is running."""

    def __init__(self, job_dir: _job_dir.ExternalJobDirectory):
        super().__init__()
        self._job_dir = job_dir
        self._entries: list[TomogramEntry] = []
        self._load_error = ""
        self._is_running = False
        self._saved = False  # True if the selection was saved in this run

        self._message = QtW.QLabel("")
        self._message.setWordWrap(True)
        self._message.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._continue_btn = QtW.QPushButton("Continue selection")
        self._continue_btn.setToolTip(
            "Continue this job to select the tomograms again, starting from the last "
            "selection."
        )
        self._continue_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._continue_btn.clicked.connect(self._continue_clicked)
        self._continue_btn.setVisible(False)
        header = QtW.QWidget()
        header_layout = QtW.QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(self._message, stretch=1)
        header_layout.addWidget(
            self._continue_btn, alignment=QtCore.Qt.AlignmentFlag.AlignTop
        )

        self._tomo_list = QTomogramCheckList(["Tomogram", "Type"])
        self._tomo_list.setFixedHeight(170)
        self._tomo_list.current_changed.connect(self._on_tomo_changed)
        self._tomo_list.checked_changed.connect(self._update_count)

        self._select_all_btn = QtW.QPushButton("Select all")
        self._select_all_btn.clicked.connect(lambda: self._check_all(True))
        self._deselect_all_btn = QtW.QPushButton("Deselect all")
        self._deselect_all_btn.clicked.connect(lambda: self._check_all(False))
        self._count_label = QtW.QLabel("")
        self._save_btn = QtW.QPushButton("Save selection")
        self._save_btn.setToolTip(
            f"Save the checked tomograms to {OUTPUT_STAR} and finish the job."
        )
        self._save_btn.clicked.connect(self._save_clicked)
        buttons = QtW.QWidget()
        buttons_layout = QtW.QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.addWidget(self._select_all_btn)
        buttons_layout.addWidget(self._deselect_all_btn)
        buttons_layout.addWidget(self._count_label, stretch=1)
        buttons_layout.addWidget(self._save_btn)

        self._filter_widget = Q2DFilterWidget()
        self._viewer = Q2DViewer()
        self._viewer.setMinimumHeight(TOMO_VIEW_MIN_HEIGHT)
        self._viewer.setMaximumHeight(TOMO_VIEW_MAX_HEIGHT)
        self._resizer = QResizer(self._viewer)
        self._filter_widget.value_changed.connect(self._viewer.redraw)

        layout = QtW.QVBoxLayout(self)
        layout.setSpacing(2)
        layout.addWidget(header)
        layout.addWidget(QtW.QLabel("<b>Tomogram Z slice</b>"))
        layout.addWidget(self._tomo_list)
        layout.addWidget(buttons)
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._viewer)
        layout.addWidget(self._resizer)
        layout.addWidget(spacer_widget())

    def on_job_updated(self, job_dir: _job_dir.ExternalJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).name in _FILES_TO_REFRESH:
            self.initialize(job_dir)

    def initialize(self, job_dir: _job_dir.ExternalJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        self._load_tomograms(job_dir)
        self._update_state(job_dir)

    def _load_tomograms(self, job_dir: _job_dir.ExternalJobDirectory):
        """Load the input tomograms. Checks are kept if the tomograms are the same."""
        in_path = job_dir.get_job_param("in_mic")
        try:
            entries = TomogramSet.from_file(job_dir.resolve_path(in_path)).entries()
        except Exception as e:
            _LOGGER.info("Failed to read the input tomograms: %s", e)
            entries = []
            self._load_error = f"Failed to read the input tomograms {in_path!r}."
        else:
            self._load_error = ""
        names = [entry.name for entry in entries]
        is_same = names == [entry.name for entry in self._entries]
        self._entries = entries
        if is_same:
            return
        was_empty = self._tomo_list.rowCount() == 0
        self._tomo_list.set_tomograms(
            [(entry.name, entry.kind) for entry in entries],
            last_selection(job_dir, names),
        )
        if not entries:
            self._viewer.clear()
            self._filter_widget.set_label_text("")
        elif not was_empty and (texts := self._tomo_list.current_row_texts()):
            self._on_tomo_changed(texts)

    def _update_state(self, job_dir: _job_dir.ExternalJobDirectory):
        """Update the check boxes, buttons and the message for the job state."""
        running = job_dir.state() is RelionJobState.RUNNING
        if not running:
            # show the selection of the last run
            names = [entry.name for entry in self._entries]
            self._tomo_list.set_checked(last_selection(job_dir, names))
            self._saved = False
        self._is_running = running
        self._tomo_list.set_checkable(running)
        for btn in (self._select_all_btn, self._deselect_all_btn, self._save_btn):
            btn.setVisible(running)
        self._continue_btn.setVisible(not running)
        self._update_count()
        self._update_message(job_dir)

    def _update_message(self, job_dir: _job_dir.ExternalJobDirectory):
        if self._load_error:
            msg = self._load_error
        elif self._is_running and self._saved:
            msg = f"Selection saved. Waiting for the job to write {OUTPUT_STAR}."
        elif self._is_running:
            msg = (
                "Check the tomograms to keep and click 'Save selection'.\n"
                "Space key toggles the check of the current tomogram."
            )
        elif job_dir.path.joinpath(OUTPUT_STAR).exists():
            num = sum(self._tomo_list.checked())
            msg = f"{num} tomograms saved in {OUTPUT_STAR}."
        else:
            msg = "Selected tomograms are not saved."
        self._message.setText(msg)

    def _update_count(self):
        checked = self._tomo_list.checked()
        num = sum(checked)
        self._count_label.setText(f"{num} / {len(checked)} selected")
        self._save_btn.setEnabled(self._is_running and num > 0)

    def _check_all(self, checked: bool):
        self._tomo_list.set_checked([checked] * self._tomo_list.rowCount())

    def _save_clicked(self):
        """Save the selection. The running job writes the output and finishes."""
        save_selection(self._job_dir, self._tomo_list.selection())
        self._saved = True
        self._update_message(self._job_dir)

    def _continue_clicked(self):
        """Open the scheduler to continue this job."""
        from .jobs import SelectTomogramsContinue

        SelectTomogramsContinue._show_scheduler_widget_for_continue(
            current_instance(), {_JOB_DIR_ARGS_NAME: self._job_dir}
        )

    def _on_tomo_changed(self, texts: tuple[str, ...]):
        """Update the viewer when the selected tomogram changes."""
        for entry in self._entries:
            if entry.name == texts[0]:
                self._show_tomogram(entry)
                return

    def _show_tomogram(self, entry: TomogramEntry):
        paths = [self._job_dir.resolve_path(p) for p in entry.paths]
        if not (existing := [p for p in paths if p.exists()]):
            self._viewer.clear()
            if paths:
                self._filter_widget.set_label_text("Tomogram file not found.")
            else:
                self._filter_widget.set_label_text("Tomogram is not reconstructed.")
            return
        if len(paths) == 1:
            tomo_view = ArrayFilteredView.from_mrc(existing[0])
        else:
            tomo_view = ArrayFilteredView.from_mrc_splits(existing)
        tomo_view.try_memmap()
        scale = float(tomo_view.get_scale())
        self._filter_widget.set_image_scale(scale if scale > 0 else 1.0)
        self._viewer.set_array_view(
            tomo_view.with_filter(self._filter_widget.apply),
            self._viewer._last_clim,
        )
        shape = (tomo_view.num_slices(),) + tomo_view.get_shape()
        self._filter_widget.set_label_text(f"{shape} {scale:.2f} Å/pix")
