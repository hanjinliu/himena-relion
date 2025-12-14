from __future__ import annotations
from pathlib import Path

from qtpy import QtWidgets as QtW
from magicgui.widgets.bases import ValueWidget
from himena_relion._widgets import QRelionNodeItem


class QPathDropWidget(QtW.QGroupBox):
    def __init__(self, type_label: str, parent=None):
        super().__init__("", parent)
        self._type_label = type_label
        self._path_label = QtW.QLabel(f"{type_label}")
        self._btn = QtW.QPushButton("Browse")
        self._btn.setFixedWidth(80)
        layout = QtW.QHBoxLayout(self)
        layout.addWidget(self._path_label)
        layout.addWidget(self._btn)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, a0):
        if isinstance(src := a0.source(), QRelionNodeItem):
            cat = src.file_type_category()
            if cat is not None and cat.startswith(self._type_label):
                a0.accept()
                return
        a0.ignore()

    def dropEvent(self, a0):
        mime = a0.mimeData()
        if mime.hasUrls():
            path_abs = Path(mime.urls()[0].toLocalFile())
            if path_abs.is_relative_to(Path.cwd()):
                path_rel = path_abs.relative_to(Path.cwd())
            else:
                path_rel = path_abs
            self._path_label.setText(path_rel.as_posix())
            a0.accept()


class PathDrop(ValueWidget):
    pass
