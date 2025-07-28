from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore
from himena_relion._widgets import JobWidgetBase, Q2DViewer, register_job
from himena_relion import _job


@register_job(_job.TomogramJobDirectory)
class QTomogramViewer(QtW.QScrollArea, JobWidgetBase):
    def __init__(self):
        super().__init__()
        self._job_dir: _job.TomogramJobDirectory = None
        self._inner = QtW.QWidget()
        self.setWidget(self._inner)
        self.setWidgetResizable(True)
        layout = QtW.QVBoxLayout(self._inner)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self._viewer = Q2DViewer()
        self._viewer.setFixedHeight(240)
        layout.addWidget(self._viewer)
        self._tomo_choice = QtW.QComboBox()
        self._tomo_choice.currentTextChanged.connect(self._on_tomo_changed)
        layout.addWidget(self._tomo_choice)

    def on_job_updated(self, job_dir: _job.TomogramJobDirectory, path: str):
        """Handle changes to the job directory."""
        self.initialize(job_dir)

    def initialize(self, job_dir: _job.TomogramJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        current_text = self._tomo_choice.currentText()
        items = []
        for info in job_dir.iter_tomogram():
            items.append(info.tomo_name)
        self._tomo_choice.clear()
        self._tomo_choice.addItems(items)
        if current_text in items:
            self._tomo_choice.setCurrentText(current_text)
        self._on_tomo_changed(self._tomo_choice.currentText())

    def _on_tomo_changed(self, text: str):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        if job_dir is None:
            return
        for info in job_dir.iter_tomogram():
            if info.tomo_name == text:
                break
        else:
            return
        tomo = info.read_tomogram()
        self._viewer.set_image(tomo)
