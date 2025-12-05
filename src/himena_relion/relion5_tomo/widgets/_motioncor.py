from __future__ import annotations
from pathlib import Path

from qtpy import QtWidgets as QtW
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    Q2DFilterWidget,
    register_job,
)
from himena_relion import _job


@register_job(_job.MotionCorrectionJobDirectory)
class QMotionCorrViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job.MotionCorrectionJobDirectory = None
        layout = self._layout

        self._viewer = Q2DViewer()
        self._filter_widget = Q2DFilterWidget()
        self._ts_choice = QtW.QComboBox()
        self._ts_choice.currentTextChanged.connect(self._ts_choice_changed)
        layout.addWidget(QtW.QLabel("<b>Motion corrected tilt series</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._viewer)
        layout.addWidget(self._ts_choice)
        self._filter_widget.value_changed.connect(self._viewer.redraw)
        self._binsize_old = -1

    def on_job_updated(self, job_dir: _job.MotionCorrectionJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".mrc":
            self._process_update(job_dir)

    def _param_changed(self):
        """Handle changes to filter parameters."""
        self._viewer.redraw()
        new_binsize = self._filter_widget.bin_factor()
        if self._binsize_old != new_binsize:
            self._binsize_old = new_binsize
            self._viewer.auto_fit()

    def initialize(self, job_dir: _job.MotionCorrectionJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir

        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        choices = [
            p.tomo_tilt_series_star_file.stem
            for p in self._job_dir.iter_corrected_tilt_series()
        ]
        index = self._ts_choice.currentIndex()
        self._ts_choice.clear()
        self._ts_choice.addItems(choices)
        if choices:
            self._ts_choice.setCurrentIndex(
                min(index if index >= 0 else 0, len(choices) - 1)
            )

    def _ts_choice_changed(self, text: str):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        if job_dir is None:
            return

        info = job_dir.corrected_tilt_series(text)
        self._filter_widget.set_image_scale(info.tomo_tilt_series_pixel_size)
        ts_view = info.read_tilt_series(job_dir.path)
        self._viewer.set_array_view(ts_view.with_filter(self._filter_widget.apply))
