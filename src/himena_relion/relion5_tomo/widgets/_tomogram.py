from __future__ import annotations
from pathlib import Path

from qtpy import QtWidgets as QtW
from himena_relion._widgets import QJobScrollArea, Q2DViewer, register_job
from himena_relion import _job


@register_job(_job.TomogramJobDirectory)
class QTomogramViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job.TomogramJobDirectory = None
        layout = self._layout

        self._viewer = Q2DViewer()
        layout.addWidget(self._viewer)
        self._tomo_choice = QtW.QComboBox()
        self._tomo_choice.currentTextChanged.connect(self._on_tomo_changed)
        layout.addWidget(self._tomo_choice)

    def on_job_updated(self, job_dir: _job.TomogramJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix not in [".out", ".err", ".star"]:
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
        self._viewer.auto_fit()

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
        tomo_view = info.read_tomogram(job_dir.path)
        self._viewer.set_array_view(tomo_view)


@register_job(_job.DenoiseJobDirectory)
class QDenoiseTomogramViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job.DenoiseJobDirectory = None
        layout = self._layout

        self._viewer = Q2DViewer()
        layout.addWidget(self._viewer)
        self._tomo_choice = QtW.QComboBox()
        self._tomo_choice.currentTextChanged.connect(self._on_tomo_changed)
        layout.addWidget(self._tomo_choice)

    def on_job_updated(self, job_dir: _job.DenoiseJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix not in [".out", ".err", ".star"]:
            self.initialize(job_dir)

    def initialize(self, job_dir: _job.DenoiseJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        if job_dir._is_train:
            return
        current_text = self._tomo_choice.currentText()
        items = []
        for info in job_dir.iter_tomogram():
            items.append(info.tomo_name)
        self._tomo_choice.clear()
        self._tomo_choice.addItems(items)
        if current_text in items:
            self._tomo_choice.setCurrentText(current_text)
        self._on_tomo_changed(self._tomo_choice.currentText())
        self._viewer.auto_fit()

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
        tomo_view = info.read_tomogram(job_dir.path)
        self._viewer.set_array_view(tomo_view)
