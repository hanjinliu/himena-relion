from __future__ import annotations
from pathlib import Path
from typing import cast
import glob
from himena import StandardType
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
        self._allowed_extensions: list[str] | None = None
        self._icon_label = QtW.QLabel()
        self._path_line_edit = QtW.QLineEdit()
        self._path_line_edit.setMinimumWidth(200)
        self._path_line_edit.setToolTip("Enter path or drag-and-drop file here")
        self._btn_browse = QtW.QPushButton("...")
        self._btn_browse.setToolTip(
            "Browse in file dialog, or right-click for more actions"
        )
        self._btn_browse.setFixedWidth(24)
        self._btn_browse.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._btn_browse.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._btn_browse.customContextMenuRequested.connect(self._on_browse_right_click)
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._icon_label)
        layout.addWidget(self._path_line_edit)
        layout.addWidget(self._btn_browse)
        self.setAcceptDrops(True)
        self._btn_browse.clicked.connect(self._on_browse_clicked)

    def get_parent_job_scheduler(self) -> QJobScheduler | None:
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, QJobScheduler):
                return parent
            parent = parent.parent()

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

    def set_allowed_extensions(self, extensions: list[str] | None) -> None:
        self._allowed_extensions = extensions

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
            caption=caption,
            start_path=start_dir,
            allowed_extensions=self._allowed_extensions,
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

    def _on_browse_right_click(self, pos):
        menu = self._make_menu()
        menu.exec(self._btn_browse.mapToGlobal(pos))

    def _make_menu(self) -> QtW.QMenu:
        menu = QtW.QMenu()
        path = self.value().strip()
        is_not_empty = len(path) > 0
        is_pattern = "*" in path or "?" in path or "[" in path

        # check if exists
        if not is_pattern:
            if Path(path).is_absolute():
                path_abs = Path(path)
            else:
                path_abs = self.get_relion_directory().joinpath(path)
            is_exist = path_abs.exists()
        else:
            is_exist = False
        action_open = menu.addAction("Open", self._open_path)
        action_glob = menu.addAction("Show matched file names", self._glob_paths)
        action_open.setEnabled(is_not_empty and not is_pattern and is_exist)
        action_glob.setEnabled(is_not_empty and is_pattern)
        return menu

    def _open_path(self):
        path = Path(self.value().strip())
        is_map = "DensityMap" in self._type_labels or "Mask3D" in self._type_labels
        if is_map and path.suffix.lower() in [".mrc", ".map"]:
            plugin = "himena_relion.io.read_density_map"
        else:
            plugin = None
        if not path.is_absolute():
            path = self.get_relion_directory().joinpath(path)
        current_instance().read_file(path, append_history=False, plugin=plugin)

    def _glob_paths(self):
        path = self.value().strip()
        path_abs = self.get_relion_directory().joinpath(path)
        matched_paths = list(glob.glob(path_abs.as_posix()))
        text = f"{len(matched_paths)} files matched\n\n" + "\n".join(
            p for p in matched_paths
        )
        current_instance().add_object(text, type=StandardType.TEXT)


class QPathDropWidgetBackend(QBaseValueWidget):
    _qwidget: QPathDropWidget

    def __init__(self, **kwargs) -> None:
        super().__init__(QPathDropWidget, "value", "setValue", "valueChanged", **kwargs)


class PathDrop(ValueWidget):
    def __init__(
        self,
        value=Undefined,
        type_label: str | list[str] = "",
        allowed_extensions: list[str] | None = None,
        **kwargs,
    ):
        super().__init__(
            widget_type=QPathDropWidgetBackend,
            value=value,
            **kwargs,
        )
        qpathdrop = cast(QPathDropWidget, self._widget._qwidget)
        qpathdrop.set_type_label(type_label)
        qpathdrop.set_allowed_extensions(allowed_extensions)
