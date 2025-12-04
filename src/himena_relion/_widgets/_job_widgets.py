"""The shared widget classes for RELION jobs."""

from __future__ import annotations

from pathlib import Path
from qtpy import QtWidgets as QtW, QtGui
from superqt.utils import qthrottled
from himena_relion import _job
from himena.consts import MonospaceFontFamily


class JobWidgetBase:
    """Widget that will be updated upon RELION job updates."""

    def on_job_updated(self, job_dir: _job.JobDirectory, fp: Path):
        """Handle updates to the job directory."""

    def initialize(self, job_dir: _job.JobDirectory):
        """Initialize the widget with the job directory."""

    def tab_title(self) -> str:
        """Return the title of the tab for this widget."""
        return "Results"


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
        self.setText(job_dir.run_out().read_text())

    def tab_title(self) -> str:
        return "run.out"


class QRunErrLog(QLogWatcher):
    def on_job_updated(self, job_dir: _job.JobDirectory, fp: Path):
        """Update the log text when run.err is updated."""
        if fp.name == "run.err":
            self.initialize(job_dir)

    def initialize(self, job_dir: _job.JobDirectory):
        self.setText(job_dir.run_err().read_text())

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
        self.setText(job_dir.note().read_text())

    def tab_title(self) -> str:
        return "note.txt"

    @qthrottled(timeout=1000)
    def _autosave_throttled(self):
        """Autosave the note.txt file when the text changes."""
        if self._job_dir is None:
            return
        note_path = self._job_dir.note()
        note_path.write_text(self.toPlainText())


class QJobStateLabel(QtW.QWidget, JobWidgetBase):
    def __init__(self):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._state_label = QtW.QLabel("Not started")

    def on_job_updated(self, job_dir, fp):
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
