from __future__ import annotations
from pathlib import Path

from qtpy import QtWidgets as QtW, QtCore
from magicgui.widgets.bases import ValueWidget
from magicgui.types import Undefined
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from himena.qt import QColoredSVGIcon
from himena_relion._utils import read_icon_svg_for_type
from himena_relion._widgets import QRelionNodeItem


class QPathDropWidget(QtW.QWidget):
    valueChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._type_labels: list[str] = []
        self._icon_label = QtW.QLabel()
        self._path_line_edit = QtW.QLineEdit()
        self._btn = QtW.QPushButton("...")
        self._btn.setToolTip("Browse in file dialog")
        self._btn.setFixedWidth(24)
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._icon_label)
        layout.addWidget(self._path_line_edit)
        layout.addWidget(self._btn)
        self.setAcceptDrops(True)
        self._btn.clicked.connect(self._on_browse_clicked)

    def set_type_label(self, label: str | list[str]) -> None:
        if isinstance(label, list):
            self._type_labels = label
        else:
            self._type_labels = [label]
        svg = read_icon_svg_for_type(label[0])
        icon = QColoredSVGIcon(svg, color="gray")
        self._icon_label.setPixmap(icon.pixmap(20, 20))

    def dragEnterEvent(self, a0):
        if isinstance(src := a0.source(), QRelionNodeItem):
            cat = src.file_type_category()
            if cat is not None and cat.startswith(tuple(self._type_labels)):
                a0.accept()
                a0.setDropAction(QtCore.Qt.DropAction.CopyAction)
                return
        a0.ignore()

    def dropEvent(self, a0):
        if isinstance(src := a0.source(), QRelionNodeItem):
            path_rel = src._filepath_rel
            self._path_line_edit.setText(path_rel.as_posix())
            a0.accept()
        # TODO: also support dragging from file explorer

    def value(self) -> str:
        return self._path_line_edit.text()

    def setValue(self, value: str) -> None:
        self._path_line_edit.setText(value)

    def _on_browse_clicked(self):
        if len(self._type_labels) == 0:
            caption = "Select file"
        elif len(self._type_labels) == 1:
            caption = f"Select {self._type_labels[0]} file"
        else:
            caption = f"Select {' or '.join(self._type_labels)} file"
        path, _ = QtW.QFileDialog.getOpenFileName(self, caption)
        if path:
            path_abs = Path(path)
            if path_abs.is_relative_to(Path.cwd()):
                path_rel = path_abs.relative_to(Path.cwd())
            else:
                path_rel = path_abs
            self._path_line_edit.setText(path_rel.as_posix())
            self.valueChanged.emit(self._path_line_edit.text())


class QPathDropWidgetBackend(QBaseValueWidget):
    _qwidget: QPathDropWidget

    def __init__(self, **kwargs) -> None:
        super().__init__(QPathDropWidget, "value", "setValue", "valueChanged", **kwargs)


class PathDrop(ValueWidget):
    def __init__(
        self,
        value=Undefined,
        type_label: str | list[str] = "",
        **kwargs,
    ):
        super().__init__(
            widget_type=QPathDropWidgetBackend,
            value=value,
            **kwargs,
        )
        self._widget._qwidget.set_type_label(type_label)
