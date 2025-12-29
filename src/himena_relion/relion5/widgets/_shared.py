import base64
import uuid
import numpy as np
from qtpy import QtWidgets as QtW, QtCore
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from io import BytesIO


class QMicrographListWidget(QtW.QTableWidget):
    current_changed = QtCore.Signal(tuple)

    def __init__(self, columns: list[str] = ("Micrograph",)):
        super().__init__()
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QtW.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(list(columns))
        self.horizontalHeader().setVisible(len(columns) > 1)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setFixedHeight(15)
        self.setVerticalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setEditTriggers(QtW.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def set_choices(self, choices: list[tuple[str, ...]]):
        """Set the micrograph choices in the list widget."""
        if self.rowCount() > 0 and self.currentItem():
            current_text = self.item(self.currentRow(), 0).text()
        else:
            current_text = None
        self.setRowCount(0)
        self.setRowCount(len(choices))
        choices_0 = []
        for i, entry in enumerate(choices):
            self.setRowHeight(i, 16)
            for j, name in enumerate(entry):
                self.setItem(i, j, QtW.QTableWidgetItem(name))
            choices_0.append(entry[0])
        if current_text and current_text in current_text:
            ith = current_text.index(current_text)
            self.setCurrentCell(ith, 0)
        elif choices:
            self.setCurrentCell(0, 0)
        self.resizeColumnsToContents()

    def _on_selection_changed(self):
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            to_emit = tuple(
                self.item(selected_rows[0].row(), col).text()
                for col in range(self.columnCount())
            )
            self.current_changed.emit(to_emit)


class QImageViewTextEdit(QtW.QTextEdit):
    def __init__(self, font_size: int = 9):
        super().__init__()
        self.setReadOnly(True)
        self._image_size_pixel = 96
        self._font_size = font_size

    def image_to_base64(self, img_slice: np.ndarray, text: str):
        img_slice_256 = ndi.zoom(
            img_slice,
            self._image_size_pixel / img_slice.shape[0],
            order=1,
            prefilter=False,
        )
        img_slice_normed = (
            (img_slice_256 - img_slice_256.min())
            / (img_slice_256.max() - img_slice_256.min())
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
