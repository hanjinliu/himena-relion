"""The shared widget classes for RELION jobs."""

from __future__ import annotations

from contextlib import suppress
from functools import lru_cache
from pathlib import Path
import sys
from typing import Iterator
from qtpy import QtWidgets as QtW, QtGui, QtCore
from superqt import QToggleSwitch
from superqt.utils import qthrottled
from himena.consts import MonospaceFontFamily
from himena.widgets import current_instance
from himena.qt import drag_files, QColoredSVGIcon
from himena_relion import _job_class, _job_dir
from himena_relion._utils import read_icon_svg, read_icon_svg_for_type
from himena_relion._pipeline import RelionPipeline
from himena_relion._widgets._job_edit import QJobParameter


class JobWidgetBase:
    """Widget that will be updated upon RELION job updates."""

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, fp: Path):
        """Handle updates to the job directory."""

    def initialize(self, job_dir: _job_dir.JobDirectory):
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


class QTextEditBase(QtW.QWidget, JobWidgetBase):
    """Text edit used for log viewing etc."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtW.QVBoxLayout(self)
        self._wordwrap_checkbox = QToggleSwitch("Word wrap")
        self._wordwrap_checkbox.setChecked(False)
        self._wordwrap_checkbox.toggled.connect(self._on_wordwrap_changed)
        self._text_edit = QtW.QPlainTextEdit()
        if sys.platform.startswith("linux"):
            # In linux, "Monospace" sometimes falls back to Sans Serif.
            # Here, we try to find a better monospace font.
            font_family = _monospace_font_for_linux()
        else:
            font_family = MonospaceFontFamily
        self.setFont(QtGui.QFont(font_family, 8))
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


class QRunOutLog(QTextEditBase):
    def on_job_updated(self, job_dir: _job_dir.JobDirectory, fp: Path):
        """Update the log text when run.out is updated."""
        if fp.name == "run.out":
            self.initialize(job_dir)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        lines: list[str] = []
        with suppress(Exception):
            with open(job_dir.path / "run.out", encoding="utf-8", newline="\n") as f:
                for line in f:
                    # run.out use "\r" to overwrite lines. Keep only the last part.
                    lines.append(line.split("\r")[-1])
            self.setText("".join(lines))

    def tab_title(self) -> str:
        return "run.out"


class QRunErrLog(QTextEditBase):
    def on_job_updated(self, job_dir: _job_dir.JobDirectory, fp: Path):
        """Update the log text when run.err is updated."""
        if fp.name == "run.err":
            self.initialize(job_dir)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        with suppress(Exception):
            self.setText(job_dir.path.joinpath("run.err").read_text(encoding="utf-8"))

    def tab_title(self) -> str:
        return "run.err"


class QNoteLog(QTextEditBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(False)
        self._job_dir: _job_dir.JobDirectory | None = None
        self._text_edit.textChanged.connect(self._autosave_throttled)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, fp: Path):
        """Handle updates to the job directory."""
        if fp.name == "note.txt":
            self.initialize(job_dir)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        self._job_dir = job_dir
        with suppress(Exception):
            self.setText(job_dir.path.joinpath("note.txt").read_text(encoding="utf-8"))

    def tab_title(self) -> str:
        return "note.txt"

    @qthrottled(timeout=1000)
    def _autosave_throttled(self):
        """Autosave the note.txt file when the text changes."""
        if self._job_dir is None:
            return
        note_path = self._job_dir.path / "note.txt"
        text = self.toPlainText()
        if note_path.read_text(encoding="utf-8") != text or not note_path.exists():
            note_path.write_text(text)


class QJobPipelineViewer(QtW.QWidget, JobWidgetBase):
    """Widget to view the input and output nodes of a RELION job."""

    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._list_widget_in = QRelionNodeList()
        self._list_widget_out = QRelionNodeList()
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

    def clear_in_out(self):
        self._list_widget_in.clear()
        self._list_widget_out.clear()

    def initialize(self, job_dir):
        path = job_dir.job_pipeline()
        self.clear_in_out()
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

    def update_item_colors(self, job_dir: _job_dir.JobDirectory):
        """Update the colors based on whether the files exist."""
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


class QJobParameterView(QJobParameter, JobWidgetBase):
    def initialize(self, job_dir: _job_dir.JobDirectory):
        self.clear_content()
        if job_cls := job_dir._to_job_class():
            self.update_by_job(job_cls)
            self._update_params(job_dir, job_cls)

    def on_job_updated(self, job_dir, fp):
        if fp.name == "job.star":
            if job_cls := job_dir._to_job_class():
                self._update_params(job_dir, job_cls)

    def _update_params(
        self,
        job_dir: _job_dir.JobDirectory,
        job_cls: type[_job_class.RelionJob],
    ):
        if issubclass(job_cls, _job_class._RelionBuiltinJob):
            self.set_parameters(
                job_cls.normalize_kwargs_inv(**job_dir.get_job_params_as_dict()),
                enabled=False,
            )

    def tab_title(self) -> str:
        return "Parameters"


class QRelionNodeList(QtW.QListWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(False)


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
            if filepath.parent.stem.startswith("job"):
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
        widget_file.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Preferred
        )
        self._press_pos = QtCore.QPoint()

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
        svg = read_icon_svg_for_type(self.file_type_category())
        return QColoredSVGIcon(svg, color="gray")

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
        font = self.font()
        font.setPointSize(font.pointSize() + 3)
        self._job_desc.setFont(font)
        self._state_label.setFont(font)

    def on_job_updated(self, job_dir, fp):
        self._on_job_updated(job_dir)

    def initialize(self, job_dir):
        self._on_job_updated(job_dir)
        self._job_desc.setText(
            f"<b><span style='color: gray;'>{job_dir.job_id}: </span> "
            f"{job_dir.job_title()}</b>"
        )

    def _on_job_updated(self, job_dir: _job_dir.JobDirectory):
        match job_dir.state():
            case _job_dir.RelionJobState.EXIT_SUCCESS:
                self._state_label.setText("Completed")
            case _job_dir.RelionJobState.EXIT_FAILURE:
                self._state_label.setText("Failed")
            case _job_dir.RelionJobState.EXIT_ABORTED:
                self._state_label.setText("Aborted")
            case _job_dir.RelionJobState.ABORT_NOW:
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
        menu.addAction("Copy Path To Clipboard", self._copy_path_to_clipboard)
        menu.addAction(
            "Copy Relative Path To Clipboard", self._copy_relative_path_to_clipboard
        )
        return menu

    def _copy_path_to_clipboard(self):
        if clipboard := QtW.QApplication.clipboard():
            clipboard.setText(str(self._path))

    def _copy_relative_path_to_clipboard(self):
        if clipboard := QtW.QApplication.clipboard():
            clipboard.setText(str(self._path_rel))


@lru_cache(maxsize=1)
def _monospace_font_for_linux() -> str:
    candidates = ["DejaVu Sans Mono", "Ubuntu Mono", "Noto Sans Mono"]
    families = QtGui.QFontDatabase.families()
    for fam in candidates:
        if fam in families:
            return fam
    return MonospaceFontFamily
