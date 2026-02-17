from __future__ import annotations

import base64
import uuid
import numpy as np
from qtpy import QtWidgets as QtW, QtCore
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from io import BytesIO

from himena_relion._utils import lowpass_filter


class QTableModel(QtCore.QAbstractTableModel):
    def __init__(self, data: list[tuple[str, ...]], columns: list[str]):
        super().__init__()
        self._data = data
        self._columns = columns

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._columns)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if orientation == QtCore.Qt.Orientation.Horizontal:
                return self._columns[section]
            else:
                return str(section + 1)

    def data(
        self,
        index: QtCore.QModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> QtCore.QVariant:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return str(self._data[index.row()][index.column()])
        return QtCore.QVariant()


class QMicrographListWidget(QtW.QTableView):
    current_changed = QtCore.Signal(tuple)

    def __init__(self, columns: list[str] = ("Micrograph",)):
        super().__init__()
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QtW.QAbstractItemView.SelectionBehavior.SelectRows)
        self._model = QTableModel([], list(columns))
        self.setModel(self._model)
        self.horizontalHeader().setVisible(len(columns) > 1)
        self.horizontalHeader().setFixedHeight(15)
        self.horizontalHeader().setStretchLastSection(True)
        self.setFixedHeight(100)
        self.setEditTriggers(QtW.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setHorizontalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.verticalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Minimum
        )
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.verticalHeader().setDefaultSectionSize(20)

    def rowCount(self) -> int:
        return self.model().rowCount()

    def current_tuple(self) -> tuple[str, ...] | None:
        sel = self.selectionModel().selectedRows()
        if sel:
            return tuple(self._model._data[sel[0].row()])

    def text(self, row: int, ncol: int = 0) -> str:
        if 0 <= row < self.rowCount():
            return self._model._data[row][ncol]
        return ""

    def current_text(self, ncol: int = 0) -> str:
        if tup := self.current_tuple():
            return tup[ncol]
        return ""

    def current_row_texts(self) -> tuple[str, ...] | None:
        return self.current_tuple()

    def set_choices(self, choices: list[tuple[str, ...]]):
        """Set the micrograph choices in the list widget."""
        was_empty = self.rowCount() == 0
        self._model._data = choices
        self._model.layoutChanged.emit()
        self.setModel(self._model)
        if self._model.columnCount() > 1 and was_empty:
            self.resizeColumnsToContents()
        if was_empty:
            self.selectRow(0)

    def _on_selection_changed(self):
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            to_emit = self.current_row_texts()
            if to_emit is not None:
                self.current_changed.emit(to_emit)

    def minimumSizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(120, 120)

    def set_current_row(self, index: int):
        """Set the current selected index."""
        if 0 <= index < self.rowCount():
            self.selectRow(index)


class QImageViewTextEdit(QtW.QTextEdit):
    """A text edit used for displaying images with text annotations."""

    def __init__(self, font_size: int = 9, image_size_pixel: int = 96):
        super().__init__()
        self.setReadOnly(True)
        self.setMinimumHeight(200)
        self._image_size_pixel = image_size_pixel
        self._font_size = font_size

    def image_to_base64(
        self,
        img_slice: np.ndarray,
        text: str = "",
        lowpass_cutoff: float = 1.0,
    ) -> str:
        img_slice_small = ndi.zoom(
            img_slice,
            self._image_size_pixel / img_slice.shape[0],
            order=1,
            prefilter=False,
        )
        img_slice_filt = lowpass_filter(img_slice_small, lowpass_cutoff)
        img_slice_normed = (
            (img_slice_filt - img_slice_filt.min())
            / (img_slice_filt.max() - img_slice_filt.min())
            * 255
        )
        img_slice = img_slice_normed.astype(np.uint8)

        pil_img = Image.fromarray(img_slice).convert("RGB")
        draw = ImageDraw.Draw(pil_img)
        font = ImageFont.load_default()
        font.size = self._font_size
        draw.text((5, 5), text, fill=(0, 255, 0), font=font)

        buffer = BytesIO()
        pil_img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return img_str

    def insert_base64_image(self, img_str: str):
        self.insertHtml(f'<img src="data:image/png;base64,{img_str}"/>')

    def prep_uuid(self) -> uuid.UUID:
        return uuid.uuid4()


class QNumParticlesLabel(QtW.QLabel):
    """A QLabel to show the number of particles."""

    def __init__(self):
        super().__init__()
        self.setText("--- particles")
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._num_particle_known = False

    def set_number(self, num: int):
        if num >= 0:
            self.setText(f"<b>{num}</b> particles")
            self._num_particle_known = True
        else:
            self.setText("??? particles")
            self._num_particle_known = False

    def set_number_for_class3d(self, num: int):
        if num >= 0:
            self.setText(f"Total <b>{num}</b> particles")
            self._num_particle_known = True
        else:
            self.setText("Total ??? particles")
            self._num_particle_known = False

    def num_known(self) -> bool:
        """Check if the number of particles is known."""
        return self._num_particle_known


class QSymmetryLabel(QtW.QLabel):
    def __init__(self):
        super().__init__()
        self.set_symmetry("C1")
        self.setStyleSheet("QSymmetryLabel { color: gray; }")
        self.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )

    def set_symmetry(self, sym_name: str):
        self.setText(f"Symmetry: <b>{sym_name}</b>")


def spacer_widget():
    spacer = QtW.QWidget()
    spacer.setSizePolicy(
        QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
    )
    return spacer


class QMoreActionButton(QtW.QPushButton):
    """A QPushButton with a dropdown menu for more actions."""

    def __init__(self, parent=None):
        super().__init__("...", parent)
        self.setFixedWidth(24)
        menu = QtW.QMenu(self)
        menu.setToolTipsVisible(True)
        self.setMenu(menu)
        self.setStyleSheet(
            "QMoreActionButton::menu-indicator { image: none; width: 0px; }"
        )
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    def add_action(self, text: str, cb):
        action = self.menu().addAction(text, cb)
        action.setToolTip(cb.__doc__ or "")
