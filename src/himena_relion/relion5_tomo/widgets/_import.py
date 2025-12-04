from __future__ import annotations
from pathlib import Path

from qtpy import QtWidgets as QtW, QtCore
from himena_relion._widgets import JobWidgetBase, Q2DViewer, register_job
from himena_relion import _job


@register_job(_job.ImportJobDirectory)
class QImportTiltSeriesViewer(QtW.QSplitter, JobWidgetBase):
    def __init__(self):
        super().__init__(QtCore.Qt.Orientation.Horizontal)
        self._left_panel = QtW.QWidget()
        # left_layout = QtW.QVBoxLayout(self._left_panel)
        self._right_panel = Q2DViewer()

        self.addWidget(self._left_panel)
        self.addWidget(self._right_panel)

    def on_job_updated(self, job_dir: _job.ImportJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix not in [".out", ".err", ".star"]:
            self.initialize(job_dir)

    def initialize(self, job_dir: _job.ImportJobDirectory):
        """Initialize the viewer with the job directory."""
        ...
