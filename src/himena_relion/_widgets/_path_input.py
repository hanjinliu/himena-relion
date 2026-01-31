from __future__ import annotations
from pathlib import Path

from qtpy import QtWidgets as QtW, QtCore
from magicgui.widgets.bases import ValueWidget
from magicgui.types import Undefined
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from himena.qt import QColoredSVGIcon
from himena.widgets import current_instance
from himena_relion._utils import read_icon_svg_for_type
from himena_relion._widgets import QRelionNodeItem, QJobScheduler


class QPathDropWidget(QtW.QWidget):
    valueChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._type_labels: list[str] = []
        self._icon_label = QtW.QLabel()
        self._path_line_edit = QtW.QLineEdit()
        self._path_line_edit.setMinimumWidth(200)
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

    def get_parent_job_scheduler(self) -> QJobScheduler | None:
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, QJobScheduler):
                return parent
            parent = parent.parent()
        return None

    def get_relion_directory(self) -> Path:
        if job_scheduler := self.get_parent_job_scheduler():
            return job_scheduler.cwd or Path.cwd()
        return Path.cwd()

    def set_type_label(self, label: str | list[str]) -> None:
        if isinstance(label, str):
            self._type_labels = [label]
        else:
            self._type_labels = list(label)
        svg = read_icon_svg_for_type(self._type_labels[0])
        icon = QColoredSVGIcon(svg, color="gray")
        self._icon_label.setPixmap(icon.pixmap(20, 20))

    def dragEnterEvent(self, a0):
        if isinstance(src := a0.source(), QRelionNodeItem):
            cat = src.file_type_category()
            if cat is not None and cat.startswith(tuple(self._type_labels)):
                a0.accept()
                a0.setDropAction(QtCore.Qt.DropAction.CopyAction)
                return
        elif a0.mimeData().hasUrls():
            # Support drag-and-drop from file explorer
            a0.accept()
            a0.setDropAction(QtCore.Qt.DropAction.CopyAction)
            return
        a0.ignore()

    def dropEvent(self, a0):
        if isinstance(src := a0.source(), QRelionNodeItem):
            path_rel = src._filepath_rel
            self._path_line_edit.setText(path_rel.as_posix())
            a0.accept()
        elif a0.mimeData().hasUrls():
            # Support drag-and-drop from file explorer
            urls = a0.mimeData().urls()
            if urls:
                path_abs = Path(urls[0].toLocalFile())
                rln_dir = self.get_relion_directory()
                if path_abs.is_relative_to(rln_dir):
                    path_rel = path_abs.relative_to(rln_dir)
                else:
                    path_rel = path_abs
                self._path_line_edit.setText(path_rel.as_posix())
                self.valueChanged.emit(self._path_line_edit.text())
                a0.accept()

    def value(self) -> str:
        return self._path_line_edit.text()

    def setValue(self, value: str) -> None:
        self._path_line_edit.setText(value)
        self.valueChanged.emit(self._path_line_edit.text())

    def _on_browse_clicked(self):
        if len(self._type_labels) == 0:
            caption = "Select file"
        elif len(self._type_labels) == 1:
            caption = f"Select {self._type_labels[0]} file"
        else:
            caption = f"Select {' or '.join(self._type_labels)} file"
        # look for .Nodes/<type_label>/ directory.
        start_dir = self.get_relion_directory().joinpath(".Nodes")
        for type_label in self._type_labels:
            candidate_dir = start_dir.joinpath(type_label)
            if candidate_dir.is_dir() and candidate_dir.exists():
                start_dir = candidate_dir
                break
        path = current_instance().exec_file_dialog(
            caption=caption, start_path=start_dir
        )
        if path:
            path_abs = Path(path).resolve()
            # .Nodes/ is not resolved yet
            if ".Nodes" in path_abs.parts:
                # path/to/.Nodes/<type label>/DIR/JOB/file.ext
                # should be reformatted to
                # path/to/DIR/JOB/file.ext
                parts = path_abs.parts
                node_index = parts.index(".Nodes")
                path_real = Path(*parts[:node_index], *parts[node_index + 2 :])
                if path_real.exists():
                    path_abs = path_real
            rln_dir = self.get_relion_directory()
            if path_abs.is_relative_to(rln_dir):
                path_rel = path_abs.relative_to(rln_dir)
            else:
                path_rel = path_abs
            self.setValue(path_rel.as_posix())


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
