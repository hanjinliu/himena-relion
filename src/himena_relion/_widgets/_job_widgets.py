"""The shared widget classes for RELION jobs."""

from __future__ import annotations

import logging
from contextlib import suppress
from pathlib import Path
import html
from typing import Any, Callable, Iterator, TYPE_CHECKING
import numpy as np
from qtpy import QtWidgets as QtW, QtGui, QtCore
from superqt import QToggleSwitch
from superqt.utils import qthrottled, GeneratorWorker
from himena.widgets import current_instance, set_status_tip
from himena.qt import drag_files, QColoredSVGIcon, QColoredToolButton
from himena.exceptions import Cancelled
from himena_relion import _job_class, _job_dir
from himena_relion._impl_objects import start_worker
from himena_relion._utils import (
    normalize_job_id,
    read_icon_svg,
    read_icon_svg_for_type,
    path_icon_svg,
    read_or_show_job,
    monospace_font_family,
)
from himena_relion._pipeline import RelionPipeline
from himena_relion._widgets._job_edit import QJobParameter
from himena_relion._widgets._misc import spacer_widget
from himena_relion.schemas._pipeline import RelionPipelineModel
from himena_relion.io import _impl

if TYPE_CHECKING:
    from himena_relion._widgets._main import QRelionJobWidget

_LOGGER = logging.getLogger(__name__)


class JobWidgetBase:
    """Widget that will be updated upon RELION job updates."""

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, fp: Path):
        """Handle updates to the job directory."""

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the widget with the job directory."""

    def widget_added_callback(self):
        """Called when the widget is added to the main window."""

    def tab_title(self) -> str:
        """Return the title of the tab for this widget."""
        return "Results"


class QJobScrollArea(QtW.QScrollArea, JobWidgetBase):
    def __init__(self):
        super().__init__()
        self.inner = QtW.QWidget()
        self.inner.setFixedWidth(420)
        self.setWidget(self.inner)
        self.setWidgetResizable(False)
        layout = QtW.QVBoxLayout(self.inner)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft
        )
        layout.setSizeConstraint(QtW.QLayout.SizeConstraint.SetMinimumSize)
        self._layout = layout
        self._worker: GeneratorWorker | None = None

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        if a0.size().width() > 420:
            self.inner.setFixedWidth(a0.size().width() - 20)

    def closeEvent(self, a0):
        self.window_closed_callback()
        return super().closeEvent(a0)

    def window_closed_callback(self):
        if self._worker is not None:
            self._worker.quit()
            self._worker = None

    def _on_yielded(self, yielded: tuple[Callable, Any] | None):
        if yielded is not None:
            fn, args = yielded
            fn(args)

    def _start_worker(self):
        self._worker.yielded.connect(self._on_yielded)
        start_worker(self._worker)


class QTextEditBase(QtW.QWidget, JobWidgetBase):
    """Text edit used for log viewing etc."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtW.QVBoxLayout(self)
        self._wordwrap_checkbox = QToggleSwitch("Word wrap")
        self._wordwrap_checkbox.setChecked(False)
        self._wordwrap_checkbox.toggled.connect(self._on_wordwrap_changed)
        self._filename_label = QtW.QLabel("")
        self._text_edit = QtW.QPlainTextEdit()
        font_family = monospace_font_family()
        self._text_edit.setFont(QtGui.QFont(font_family, 8))
        self._text_edit.setReadOnly(True)
        self._text_edit.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self._text_edit.setUndoRedoEnabled(False)
        header_layout = QtW.QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(self._wordwrap_checkbox)
        header_layout.addWidget(
            self._filename_label, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        layout.addLayout(header_layout)
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
        hbar = self._text_edit.horizontalScrollBar()
        vval_old = vbar.value()
        hval_old = hbar.value()
        is_bottom = vval_old > vbar.maximum() - 5
        sel0 = self._text_edit.textCursor().selectionStart()
        sel1 = self._text_edit.textCursor().selectionEnd()
        self._text_edit.setPlainText(text)

        # if the vertical scrollbar was at the bottom, keep it at the bottom, otherwise
        # keep the previous position.
        if is_bottom:
            vbar.setValue(vbar.maximum())
        else:
            vbar.setValue(min(vval_old, vbar.maximum()))
        hbar.setValue(min(hval_old, hbar.maximum()))

        # restore text selection
        max_position = len(text)
        self._text_edit.textCursor().setPosition(min(sel0, max_position))
        self._text_edit.textCursor().setPosition(
            min(sel1, max_position), QtGui.QTextCursor.MoveMode.KeepAnchor
        )

    def setReadOnly(self, readonly: bool):
        self._text_edit.setReadOnly(readonly)


class QRunOutErrLog(QtW.QSplitter, JobWidgetBase):
    """Combined log viewer for run.out and run.err."""

    def __init__(self):
        super().__init__(QtCore.Qt.Orientation.Vertical)
        self._out_log = QRunOutLog()
        self._err_log = QRunErrLog()
        self.addWidget(self._out_log)
        self._out_log._filename_label.setText("run.out")
        self._err_log._filename_label.setText("run.err")
        self.addWidget(self._err_log)
        self.setSizes([600, 300])

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, fp: Path):
        if fp.name == "run.out":
            self._out_log.initialize(job_dir)
        elif fp.name == "run.err":
            self._err_log.initialize(job_dir)
        elif fp.name.startswith("RELION_JOB_"):
            self._out_log.initialize(job_dir)
            self._err_log.initialize(job_dir)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        self._out_log.initialize(job_dir)
        self._err_log.initialize(job_dir)

    def tab_title(self) -> str:
        return "Logs"

    def last_lines(self) -> str:
        """Return the last two lines of run.out log."""
        return f"{self._out_log._second_last_line}\n{self._out_log._last_line}"


class QRunOutLog(QTextEditBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_line = ""
        self._second_last_line = ""

    def initialize(self, job_dir: _job_dir.JobDirectory):
        lines: list[str] = []
        with suppress(Exception):
            with open(job_dir.path / "run.out", encoding="utf-8", newline="\n") as f:
                for line in f:
                    # run.out use "\r" to overwrite lines. Keep only the last part.
                    lines.append(line.split("\r")[-1])
            self._last_line = self._second_last_line = ""
            for line in reversed(lines):
                line = line.strip()
                if line != "":
                    if self._last_line == "":
                        self._last_line = line
                    else:
                        self._second_last_line = line
                        break
            self.setText("".join(lines))


class QRunErrLog(QTextEditBase):
    def initialize(self, job_dir: _job_dir.JobDirectory):
        with suppress(Exception):
            self.setText(job_dir.path.joinpath("run.err").read_text(encoding="utf-8"))


class QNoteEdit(QTextEditBase):
    """Editable text edit area for note.txt."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(False)
        self._job_dir: _job_dir.JobDirectory | None = None
        self._text_edit.textChanged.connect(self._autosave_throttled)
        self._filename_label.setText("note.txt")

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, fp: Path):
        """Handle updates to the job directory."""
        if fp.name.startswith("RELION_JOB_"):
            # note.txt is updated only when JOB started.
            self.initialize(job_dir)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        self._job_dir = job_dir
        with suppress(Exception):
            # Check if the content is different before setting text. Without this,
            # text will be initialized every time after the autosave, causing cursor
            # jump.
            incoming = job_dir.path.joinpath("note.txt").read_text(encoding="utf-8")
            if incoming != self.toPlainText():
                self.setText(incoming)

    def tab_title(self) -> str:
        return "Note"

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
            item = QRelionNodeItem(
                rln_dir,
                input_path,
                filetype=input_node.type_label,
            )
            list_item = QtW.QListWidgetItem(self._list_widget_in)
            list_item.setSizeHint(item.sizeHint())
            self._list_widget_in.addItem(list_item)
            self._list_widget_in.setItemWidget(list_item, item)
        if len(job_pipeline.outputs) == 0:
            # Some jobs, such as "split particles", do not have output nodes but the
            # default pipeline will be updated after the job finishes.
            default = RelionPipeline.from_star(rln_dir / "default_pipeline.star")
            outputs = []
            this_job_id = job_dir.job_normal_id()
            for each in default.outputs:
                if normalize_job_id(each.path_job) == this_job_id:
                    outputs.append(each)
        else:
            outputs = job_pipeline.outputs
        for output_node in outputs:
            output_path = rln_dir / output_node.path
            item = QRelionNodeItem(
                rln_dir,
                output_path,
                filetype=output_node.type_label,
                show_dir=False,
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
    """Parameter view in the Parameters tab."""

    def initialize(self, job_dir: _job_dir.JobDirectory):
        self.clear_content()
        if job_cls := job_dir._to_job_class():
            self.update_by_job(job_cls)
            self._update_params(job_dir, job_cls)
        else:
            _LOGGER.warning(
                "Cannot determine the job class for %s",
                job_dir.job_normal_id(),
            )

    def on_job_updated(self, job_dir, fp):
        if fp.name == "job.star":
            if job_cls := job_dir._to_job_class():
                self._update_params(job_dir, job_cls)

    def _update_params(
        self,
        job_dir: _job_dir.JobDirectory,
        job_cls: type[_job_class.RelionJob],
    ):
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
        relion_dir: Path,
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
            try:
                self._filepath_rel = filepath.relative_to(relion_dir)
            except ValueError:
                self._filepath_rel = filepath
            if filepath.parent.stem.startswith("job"):
                widget_dir = QFileLabel(
                    self,
                    path=filepath.parent,
                    path_rel=self._filepath_rel.parent,
                    icon_label=self.item_icon_label(is_dir=True),
                )
                widget_dir.dragged.connect(self._drag_dir_event)
                widget_dir.double_clicked.connect(self._open_dir_event)
            else:
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
        set_status_tip(f"Start dragging directory {self._filepath.parent}", duration=5)
        drag_files(
            self._filepath.parent,
            desc=self._filepath_rel.parent.as_posix(),
            source=self,
        )

    def _open_dir_event(self):
        if not (path := self._filepath.parent).exists():
            raise FileNotFoundError(f"Directory {path} does not exist.")
        read_or_show_job(current_instance(), path)

    def _drag_file_event(self):
        set_status_tip(f"Start dragging file {self._filepath}", duration=5)
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
    """Label that shows the current job title, state etc."""

    def __init__(self, parent: QRelionJobWidget):
        super().__init__(parent)
        self._job_widget = parent
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._job_desc = QtW.QLabel("XXX")
        self._job_desc.setSizePolicy(
            QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Minimum
        )
        self._set_alias_btn = QColoredToolButton(
            self._run_set_alias, path_icon_svg("edit")
        )
        self._set_alias_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._set_alias_btn.setFixedSize(18, 18)
        self._set_alias_btn.update_color("gray")
        self._state_label = QtW.QLabel("Not started")
        self._state_label.setSizePolicy(
            QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Minimum
        )
        self._state_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self._job_desc)
        layout.addWidget(
            self._set_alias_btn, alignment=QtCore.Qt.AlignmentFlag.AlignLeft
        )
        layout.addWidget(spacer_widget())
        layout.addWidget(self._state_label)
        font = self.font()
        font.setPointSize(font.pointSize() + 3)
        self._job_desc.setFont(font)
        font.setPointSize(font.pointSize() - 1)
        self._state_label.setFont(font)
        self.setFixedHeight(27)

    def on_job_updated(self, job_dir, fp):
        if fp.name == "default_pipeline.star" or fp.suffix == "":
            self._on_job_updated(job_dir)

    def initialize(self, job_dir):
        self._on_job_updated(job_dir)
        # look for alias
        pipeline = RelionPipelineModel.validate_file(
            job_dir.relion_project_dir / "default_pipeline.star"
        )
        is_eq = pipeline.processes.process_name.eq(job_dir.job_normal_id())
        is_eq_idx = np.where(is_eq)
        title = job_dir.job_title()
        if len(is_eq_idx[0]) > 0:
            alias = pipeline.processes.alias[int(is_eq_idx[0][0])]
            if alias.count("/") == 2:
                alias_latter = alias.split("/")[1]
                title = html.escape(f"{alias_latter} ({title})")
        self._job_desc.setText(
            f"<b><span style='color: gray;'>{job_dir.job_number}: </span> {title}</b>"
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
                if job_dir.is_scheduled():
                    self._state_label.setText("Scheduled")
                else:
                    self._state_label.setText("Running")
        metric = QtGui.QFontMetrics(self._state_label.font())
        text_width = metric.horizontalAdvance(self._state_label.text())
        self._state_label.setFixedWidth(text_width + 10)

    def _run_set_alias(self):
        """Set alias for the job."""
        job_widget = self._job_widget
        if ui := job_widget._ui_ref():
            with suppress(Cancelled):
                _impl.set_job_alias(ui, job_widget._job_dir)


class QFileLabel(QtW.QWidget):
    """A widget with label such as Import/job001/ that can be dragged."""

    dragged = QtCore.Signal()
    right_clicked = QtCore.Signal(QtCore.QPoint)
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
        self._pressed_pos = a0.pos()

    def mouseMoveEvent(self, a0):
        if (
            a0.buttons() & QtCore.Qt.MouseButton.LeftButton
            and not self._pressed_pos.isNull()
        ):
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
        menu = QtW.QMenu(self)
        menu.addAction("Open", self._open_path)
        menu.addSeparator()
        menu.addAction("Copy Path To Clipboard", self._copy_path_to_clipboard)
        menu.addAction(
            "Copy Relative Path To Clipboard", self._copy_rel_path_to_clipboard
        )
        return menu

    def _open_path(self):
        if not (path := self._path).exists():
            raise FileNotFoundError(f"File {path} does not exist.")
        current_instance().read_file(
            path,
            plugin=self._relion_node_item._plugin_for_filetype(),
        )

    def _copy_path_to_clipboard(self):
        if clipboard := QtW.QApplication.clipboard():
            clipboard.setText(str(self._path))

    def _copy_rel_path_to_clipboard(self):
        if clipboard := QtW.QApplication.clipboard():
            clipboard.setText(str(self._path_rel))
