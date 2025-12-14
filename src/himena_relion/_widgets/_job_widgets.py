"""The shared widget classes for RELION jobs."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator
from qtpy import QtWidgets as QtW, QtGui, QtCore
from superqt import QToggleSwitch
from superqt.utils import qthrottled
from himena_relion import _job
from himena.consts import MonospaceFontFamily
from himena.widgets import current_instance
from himena.qt import drag_files, QColoredSVGIcon
from himena_relion._utils import read_icon_svg
from himena_relion._pipeline import RelionPipeline


class JobWidgetBase:
    """Widget that will be updated upon RELION job updates."""

    def on_job_updated(self, job_dir: _job.JobDirectory, fp: Path):
        """Handle updates to the job directory."""

    def initialize(self, job_dir: _job.JobDirectory):
        """Initialize the widget with the job directory."""

    def tab_title(self) -> str:
        """Return the title of the tab for this widget."""
        return "Results"


class QJobScrollArea(QtW.QScrollArea, JobWidgetBase):
    def __init__(self):
        super().__init__()
        inner = QtW.QWidget()
        self.setWidget(inner)
        self.setWidgetResizable(True)
        layout = QtW.QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignHCenter
        )
        self._layout = layout


class QLogWatcher(QtW.QWidget, JobWidgetBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtW.QVBoxLayout(self)
        self._wordwrap_checkbox = QToggleSwitch("Word wrap")
        self._wordwrap_checkbox.setChecked(False)
        self._wordwrap_checkbox.toggled.connect(self._on_wordwrap_changed)
        self._text_edit = QtW.QTextEdit()
        self.setFont(QtGui.QFont(MonospaceFontFamily, 8))
        self._text_edit.setReadOnly(True)
        self._text_edit.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self._text_edit.setUndoRedoEnabled(False)
        layout.addWidget(self._wordwrap_checkbox)
        layout.addWidget(self._text_edit)

    def _on_wordwrap_changed(self, checked: bool):
        if checked:
            self._text_edit.setWordWrapMode(QtGui.QTextOption.WrapMode.WordWrap)
        else:
            self._text_edit.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)

    def toPlainText(self) -> str:
        return self._text_edit.toPlainText()

    def setText(self, text: str):
        vbar = self._text_edit.verticalScrollBar()
        val_old = vbar.value()
        self._text_edit.setPlainText(text)
        vbar.setValue(min(val_old, vbar.maximum()))

    def setReadOnly(self, readonly: bool):
        self._text_edit.setReadOnly(readonly)


class QRunOutLog(QLogWatcher):
    def on_job_updated(self, job_dir: _job.JobDirectory, fp: Path):
        """Update the log text when run.out is updated."""
        if fp.name == "run.out":
            self.initialize(job_dir)

    def initialize(self, job_dir: _job.JobDirectory):
        lines: list[str] = []
        with open(job_dir.run_out(), encoding="utf-8", newline="\n") as f:
            for line in f:
                # run.out use "\r" to overwrite lines. Keep only the last part.
                lines.append(line.split("\r")[-1])
        self.setText("".join(lines))

    def tab_title(self) -> str:
        return "run.out"


class QRunErrLog(QLogWatcher):
    def on_job_updated(self, job_dir: _job.JobDirectory, fp: Path):
        """Update the log text when run.err is updated."""
        if fp.name == "run.err":
            self.initialize(job_dir)

    def initialize(self, job_dir: _job.JobDirectory):
        self.setText(job_dir.run_err().read_text(encoding="utf-8"))

    def tab_title(self) -> str:
        return "run.err"


class QNoteLog(QLogWatcher):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(False)
        self._job_dir: _job.JobDirectory | None = None
        self._text_edit.textChanged.connect(self._autosave_throttled)

    def on_job_updated(self, job_dir: _job.JobDirectory, fp: Path):
        """Handle updates to the job directory."""
        if fp.name == "note.txt":
            self.initialize(job_dir)

    def initialize(self, job_dir: _job.JobDirectory):
        self._job_dir = job_dir
        self.setText(job_dir.note().read_text(encoding="utf-8"))

    def tab_title(self) -> str:
        return "note.txt"

    @qthrottled(timeout=1000)
    def _autosave_throttled(self):
        """Autosave the note.txt file when the text changes."""
        if self._job_dir is None:
            return
        note_path = self._job_dir.note()
        text = self.toPlainText()
        if note_path.read_text(encoding="utf-8") != text:
            note_path.write_text(text)


class QJobInOut(QtW.QWidget, JobWidgetBase):
    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._list_widget_in = QtW.QListWidget()
        self._list_widget_in.setAcceptDrops(False)
        self._list_widget_out = QtW.QListWidget()
        self._list_widget_in.setAcceptDrops(False)
        layout.addWidget(QtW.QLabel("<b>Inputs</b>"))
        layout.addWidget(self._list_widget_in)
        layout.addWidget(QtW.QLabel("<b>Outputs</b>"))
        layout.addWidget(self._list_widget_out)

    def dragEnterEvent(self, a0):
        a0.ignore()

    def on_job_updated(self, job_dir, fp):
        if fp.name == "job_pipeline.star":
            self.initialize(job_dir)
        elif fp.suffix in [".mrc", ".star"]:
            self.update_item_colors(job_dir)

    def initialize(self, job_dir):
        path = job_dir.job_pipeline()
        self._list_widget_in.clear()
        self._list_widget_out.clear()
        if not path.exists():
            return
        rln_dir = job_dir.relion_project_dir

        job_pipeline = RelionPipeline.from_star(path)
        for input_node in job_pipeline.inputs:
            input_path = rln_dir / input_node.path
            item = QRelionNodeItem(input_path, filetype=input_node.type_label)
            list_item = QtW.QListWidgetItem(self._list_widget_in)
            list_item.setSizeHint(item.sizeHint())
            self._list_widget_in.addItem(list_item)
            self._list_widget_in.setItemWidget(list_item, item)
        for output_node in job_pipeline.outputs:
            output_path = rln_dir / output_node.path
            item = QRelionNodeItem(
                output_path, filetype=output_node.type_label, show_dir=False
            )
            list_item = QtW.QListWidgetItem(self._list_widget_out)
            list_item.setSizeHint(item.sizeHint())
            self._list_widget_out.addItem(list_item)
            self._list_widget_out.setItemWidget(list_item, item)

    def update_item_colors(self, job_dir: _job.JobDirectory):
        rln_dir = job_dir.relion_project_dir
        text_color = self.palette().text().color().name()
        for item_widget in self._iter_output_node_items():
            for labels in item_widget.draggable_widgets:
                if labels.path_exists(rln_dir):
                    labels.label_widget.setStyleSheet(f"color: {text_color};")
                else:
                    labels.label_widget.setStyleSheet("color: gray;")

    def _iter_output_node_items(self) -> Iterator[QRelionNodeItem]:
        for i in range(self._list_widget_out.count()):
            list_item = self._list_widget_out.item(i)
            item_widget = self._list_widget_out.itemWidget(list_item)
            if isinstance(item_widget, QRelionNodeItem):
                yield item_widget

    def tab_title(self) -> str:
        return "In/Out"


class QRelionNodeItem(QtW.QWidget):
    def __init__(
        self,
        filepath: Path,
        filetype: str | None = None,
        show_dir: bool = True,
    ):
        super().__init__()
        self._filepath = filepath
        self._filetype = filetype
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.draggable_widgets: list[QFileLabel] = []
        if show_dir:
            if self._filepath.parent.stem.startswith("job"):
                self._filepath_rel = Path(*filepath.parts[-3:])
                widget_dir = QFileLabel(
                    self,
                    path=filepath.parent,
                    path_rel=self._filepath_rel.parent,
                    icon_label=self.item_icon_label(is_dir=True),
                )
                widget_dir.dragged.connect(self._drag_dir_event)
                widget_dir.double_clicked.connect(self._open_dir_event)
            else:
                self._filepath_rel = filepath
                widget_dir = QFileLabel(self)
            widget_dir.setFixedWidth(170)
            layout.addWidget(widget_dir)
            self.draggable_widgets.append(widget_dir)
        else:
            self._filepath_rel = Path(*filepath.parts[-3:])

        widget_file = QFileLabel(
            self,
            path=filepath,
            path_rel=self._filepath_rel,
            icon_label=self.item_icon_label(),
            text=self._filepath.name if show_dir else None,
        )
        widget_file.dragged.connect(self._drag_file_event)
        widget_file.double_clicked.connect(self._open_file_event)
        self.draggable_widgets.append(widget_file)
        self.setToolTip(f"{self._filepath_rel.as_posix()}\nType: {self._filetype}")

        layout.addWidget(widget_file)

    def file_type_category(self) -> str | None:
        if self._filetype is None:
            return None
        return self._filetype.split(".")[0]

    def item_icon_label(self, is_dir: bool = False) -> QtW.QLabel:
        qiconlabel = QtW.QLabel()
        qiconlabel.setFixedSize(20, 20)
        if is_dir:
            icon = QColoredSVGIcon(read_icon_svg("folder"), color="gray")
        else:
            icon = self._icon_for_filetype()
        qiconlabel.setPixmap(icon.pixmap(18, 18))
        return qiconlabel

    def _icon_for_filetype(self) -> QtGui.QIcon:
        match self.file_type_category():
            case "DensityMap":
                return QColoredSVGIcon(read_icon_svg("density"), color="gray")
            case "Mask3D":
                return QColoredSVGIcon(read_icon_svg("mask"), color="gray")
            case "TomoOptimisationSet":
                return QColoredSVGIcon(read_icon_svg("star"), color="gray")
            case "TomogramGroupMetadata":
                return QColoredSVGIcon(read_icon_svg("tomograms"), color="gray")
            case "ParticleGroupMetadata":
                return QColoredSVGIcon(read_icon_svg("particles"), color="gray")
            case _:
                return QColoredSVGIcon(read_icon_svg("file"), color="gray")

    def _drag_dir_event(self):
        drag_files(
            self._filepath.parent,
            desc=self._filepath_rel.parent.as_posix(),
            source=self,
        )

    def _open_dir_event(self):
        if not (path := self._filepath.parent).exists():
            raise FileNotFoundError(f"Directory {path} does not exist.")
        current_instance().read_file(path)

    def _drag_file_event(self):
        drag_files(
            self._filepath,
            desc=self._filepath_rel.as_posix(),
            source=self,
            plugin=self._plugin_for_filetype(),
        )

    def _open_file_event(self):
        if not (path := self._filepath).exists():
            raise FileNotFoundError(f"File {path} does not exist.")
        current_instance().read_file(
            path,
            plugin=self._plugin_for_filetype(),
        )

    def _plugin_for_filetype(self) -> str | None:
        match self.file_type_category():
            case "DensityMap" | "Mask3D":
                return "himena_relion.io.read_density_map"
            case _:
                return None


class QJobStateLabel(QtW.QWidget, JobWidgetBase):
    def __init__(self):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._job_desc = QtW.QLabel("XXX")
        self._state_label = QtW.QLabel("Not started")
        self._state_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._job_desc)
        layout.addWidget(self._state_label)

    def on_job_updated(self, job_dir, fp):
        self._on_job_updated(job_dir)

    def initialize(self, job_dir):
        self._on_job_updated(job_dir)
        self._job_desc.setText(
            f"<b><span style='color: gray;'>{job_dir.job_id}: </span> "
            f"{job_dir.job_type_repr}</b>"
        )

    def _on_job_updated(self, job_dir: _job.JobDirectory):
        match job_dir.state():
            case _job.RelionJobState.EXIT_SUCCESS:
                self._state_label.setText("Completed")
            case _job.RelionJobState.EXIT_FAILURE:
                self._state_label.setText("Failed")
            case _job.RelionJobState.EXIT_ABORTED:
                self._state_label.setText("Aborted")
            case _job.RelionJobState.ABORT_NOW:
                self._state_label.setText("Aborting")
            case _:
                self._state_label.setText("Running")


class QFileLabel(QtW.QWidget):
    dragged = QtCore.Signal()
    right_clicked = QtCore.Signal()
    double_clicked = QtCore.Signal()

    def __init__(
        self,
        parent: QRelionNodeItem,
        path: Path | None = None,
        path_rel: Path | None = None,
        icon_label: QtW.QLabel | None = None,
        text: str | None = None,
    ):
        super().__init__(parent)
        self._path = path
        self._path_rel = path_rel
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        if icon_label:
            layout.addWidget(icon_label)
        self._pressed_pos = QtCore.QPoint()
        self._enabled = False
        if path and path_rel:
            if text:
                qlabel = QtW.QLabel(text)
            else:
                qlabel = QtW.QLabel(path_rel.as_posix())
            if not path.exists():
                qlabel.setStyleSheet("color: gray;")
            else:
                self.right_clicked.connect(lambda p: self._make_context_menu().exec(p))
                self._enabled = True
        else:
            qlabel = QtW.QLabel("--")
            qlabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(qlabel)
        self.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
        self._label_widget = qlabel
        self._relion_node_item = parent

    @property
    def label_widget(self) -> QtW.QLabel:
        return self._label_widget

    def relion_node_item(self) -> QRelionNodeItem:
        return self._relion_node_item

    def path_exists(self, relion_dir: Path) -> bool:
        return self._path.exists() or relion_dir.joinpath(self._path_rel).exists()

    def mousePressEvent(self, a0):
        if a0.button() == QtCore.Qt.MouseButton.LeftButton:
            self._pressed_pos = a0.pos()

    def mouseMoveEvent(self, a0):
        if not self._pressed_pos.isNull():
            self._pressed_pos = QtCore.QPoint()
            self.dragged.emit()

    def mouseReleaseEvent(self, a0):
        if (
            a0.button() == QtCore.Qt.MouseButton.RightButton
            and not self._pressed_pos.isNull()
        ):
            self.right_clicked.emit(self.mapToGlobal(self._pressed_pos))
        self._pressed_pos = QtCore.QPoint()

    def mouseDoubleClickEvent(self, a0):
        if a0.button() == QtCore.Qt.MouseButton.LeftButton:
            self.double_clicked.emit()

    def _make_context_menu(self):
        menu = QtW.QMenu()
        menu.addAction("Copy full path to clipboard", self._copy_path_to_clipboard)
        menu.addAction(
            "Copy relative path to clipboard", self._copy_relative_path_to_clipboard
        )
        return menu

    def _copy_path_to_clipboard(self):
        if clipboard := QtW.QApplication.clipboard():
            clipboard.setText(str(self._path))

    def _copy_relative_path_to_clipboard(self):
        if clipboard := QtW.QApplication.clipboard():
            clipboard.setText(str(self._path_rel))
