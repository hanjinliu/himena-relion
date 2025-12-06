from __future__ import annotations
from pathlib import Path

import numpy as np
from qtpy import QtWidgets as QtW
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    Q2DFilterWidget,
    register_job,
)
from himena_relion import _job


@register_job(_job.TomogramJobDirectory)
class QTomogramViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job.TomogramJobDirectory = None
        layout = self._layout

        self._viewer = Q2DViewer()
        self._filter_widget = Q2DFilterWidget()
        self._filter_widget._bin_factor.setText("1")
        self._tomo_choice = QtW.QComboBox()
        self._tomo_choice.currentTextChanged.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Tomogram Z slice</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._tomo_choice)
        layout.addWidget(self._viewer)
        self._filter_widget.value_changed.connect(self._viewer.redraw)

    def on_job_updated(self, job_dir: _job.TomogramJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix not in [".out", ".err", ".star"]:
            self.initialize(job_dir)

    def initialize(self, job_dir: _job.TomogramJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        current_text = self._tomo_choice.currentText()
        items = [info.tomo_name for info in job_dir.iter_tomogram()]
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
        tomo_view = info.read_tomogram(job_dir.relion_project_dir)
        if (pixel_size := info.tomo_pixel_size) > 0:
            self._filter_widget.set_image_scale(pixel_size)
        self._viewer.set_array_view(tomo_view.with_filter(self._filter_widget.apply))


@register_job(_job.DenoiseJobDirectory)
class QDenoiseTomogramViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job.DenoiseJobDirectory = None
        layout = self._layout

        self._viewer = Q2DViewer()
        self._tomo_choice = QtW.QComboBox()
        self._tomo_choice.currentTextChanged.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Denoised tomogram Z slice</b>"))
        layout.addWidget(self._tomo_choice)
        layout.addWidget(self._viewer)

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
        items = [info.tomo_name for info in job_dir.iter_tomogram()]
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
        tomo_view = info.read_tomogram(job_dir.relion_project_dir)
        self._viewer.set_array_view(tomo_view)


@register_job(_job.PickJobDirectory)
class PickViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job.PickJobDirectory = None
        layout = self._layout

        self._viewer = Q2DViewer()
        self._filter_widget = Q2DFilterWidget()
        self._filter_widget._bin_factor.setText("1")
        self._tomo_choice = QtW.QComboBox()
        self._tomo_choice.currentTextChanged.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Picked tomogram Z slice</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._tomo_choice)
        layout.addWidget(self._viewer)
        self._filter_widget.value_changed.connect(self._viewer.redraw)

    def on_job_updated(self, job_dir: _job.PickJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix not in [".out", ".err", ".star"]:
            self.initialize(job_dir)

    def initialize(self, job_dir: _job.PickJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        current_text = self._tomo_choice.currentText()
        items = [info.tomo_name for info in job_dir.iter_tomogram()]
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
        tomo_view = info.read_tomogram(job_dir.relion_project_dir)
        if getter := info.get_particles:
            cols = [f"rlnCenteredCoordinate{x}Angst" for x in "ZYX"]
            points = getter()[cols].to_numpy(dtype=np.float32) / info.tomo_pixel_size
            center = (
                np.array(info.tomo_shape, dtype=np.float32) / info.tomogram_binning - 1
            ) / 2
            self._viewer.set_points(points + center[np.newaxis])
        self._viewer.set_array_view(tomo_view)
