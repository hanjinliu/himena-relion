"""The shared widget classes for RELION jobs."""

from __future__ import annotations

from pathlib import Path
from qtpy import QtWidgets as QtW, QtGui, QtCore
import starfile
from superqt.utils import qthrottled
from himena_relion import _job
from himena.consts import MonospaceFontFamily
from himena.qt import drag_files
from himena_builtins.qt.widgets._dragarea import QDraggableArea


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


class QLogWatcher(QtW.QTextEdit, JobWidgetBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QtGui.QFont(MonospaceFontFamily, 10))
        self.setReadOnly(True)
        self.setLineWrapMode(QtW.QTextEdit.LineWrapMode.NoWrap)
        self.setUndoRedoEnabled(False)


class QRunOutLog(QLogWatcher):
    def on_job_updated(self, job_dir: _job.JobDirectory, fp: Path):
        """Update the log text when run.out is updated."""
        if fp.name == "run.out":
            self.initialize(job_dir)

    def initialize(self, job_dir: _job.JobDirectory):
        self.setText(job_dir.run_out().read_text(encoding="utf-8"))

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
        self.textChanged.connect(self._autosave_throttled)

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
        self._list_widget_out = QtW.QListWidget()
        layout.addWidget(QtW.QLabel("<b>Inputs</b>"))
        layout.addWidget(self._list_widget_in)
        layout.addWidget(QtW.QLabel("<b>Outputs</b>"))
        layout.addWidget(self._list_widget_out)

    def on_job_updated(self, job_dir, fp):
        if fp.name == "job_pipeline.star":
            self.initialize(job_dir)

    def initialize(self, job_dir):
        path = job_dir.job_pipeline()
        self._list_widget_in.clear()
        self._list_widget_out.clear()
        if not path.exists():
            return
        df_in = starfile.read(path, always_dict=True).get("pipeline_input_edges", None)
        rln_dir = job_dir.relion_project_dir
        if df_in is not None:
            for input_path_rel in df_in["rlnPipeLineEdgeFromNode"]:
                # such as Select/job016/particles.star
                input_path = rln_dir / input_path_rel
                item = QRelionNodeItem(input_path)
                list_item = QtW.QListWidgetItem(self._list_widget_in)
                list_item.setSizeHint(item.sizeHint())
                self._list_widget_in.addItem(list_item)
                self._list_widget_in.setItemWidget(list_item, item)

        df_out = starfile.read(path, always_dict=True).get(
            "pipeline_output_edges", None
        )
        if df_out is not None:
            for output_path_rel in df_out["rlnPipeLineEdgeToNode"]:
                # such as Class3D/job017/run_it025_data.star
                if Path(output_path_rel).is_absolute():
                    output_path = Path(output_path_rel)
                else:
                    output_path = rln_dir / output_path_rel
                item = QRelionNodeItem(output_path, show_dir=False)
                list_item = QtW.QListWidgetItem(self._list_widget_out)
                list_item.setSizeHint(item.sizeHint())
                self._list_widget_out.addItem(list_item)
                self._list_widget_out.setItemWidget(list_item, item)

    def tab_title(self) -> str:
        return "In/Out"


class QRelionNodeItem(QtW.QWidget):
    def __init__(self, filepath: Path, show_dir: bool = True):
        super().__init__()
        self._filepath = filepath
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        if show_dir:
            if self._filepath.parent.stem.startswith("job"):
                self._filepath_rel = Path(*filepath.parts[-3:])
                drag_dir = QDraggableArea()
                drag_dir.setFixedSize(20, 20)
                drag_dir.dragged.connect(self._drag_dir_event)
                drag_dir.setToolTip("Drag this job directory.")
                qlabel = QtW.QLabel("/".join(filepath.parts[-3:-1]) + "/")
                qlabel.setFixedWidth(150)
                layout.addWidget(qlabel)
                layout.addWidget(drag_dir)
            else:
                self._filepath_rel = filepath
                empty0 = QtW.QLabel("--")
                empty0.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                empty0.setFixedWidth(150)
                empty1 = QtW.QLabel()
                empty1.setFixedSize(20, 20)
                layout.addWidget(empty0)
                layout.addWidget(empty1)
        else:
            self._filepath_rel = Path(*filepath.parts[-3:])

        drag_file = QDraggableArea()
        drag_file.setFixedSize(20, 20)
        drag_file.dragged.connect(self._drag_file_event)
        drag_file.setToolTip("Drag this file.")
        qlabel = QtW.QLabel(filepath.name)
        layout.addWidget(qlabel)
        qlabel.setFixedWidth(140 if show_dir else 280)
        layout.addWidget(drag_file)

    def _drag_dir_event(self):
        drag_files(
            self._filepath.parent,
            desc=self._filepath_rel.parent.as_posix(),
            source=self,
        )

    def _drag_file_event(self):
        drag_files(
            self._filepath,
            desc=self._filepath_rel.as_posix(),
            source=self,
        )


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
                self._state_label.setText("Aborting ...")
            case _:
                self._state_label.setText("Unknown")
