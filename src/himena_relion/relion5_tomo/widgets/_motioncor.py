from __future__ import annotations
from pathlib import Path

from qtpy import QtWidgets as QtW
from himena_relion._widgets import JobWidgetBase, Q2DViewer, register_job
from himena_relion import _job
from himena_relion.relion5_tomo.widgets._shared import standard_layout


@register_job(_job.MotionCorrectionJobDirectory)
class QMotionCorrViewer(QtW.QScrollArea, JobWidgetBase):
    def __init__(self):
        super().__init__()
        self._job_dir: _job.MotionCorrectionJobDirectory = None
        layout = standard_layout(self)

        self._viewer = Q2DViewer()
        self._viewer.setFixedSize(300, 300)
        layout.addWidget(self._viewer)
        self._ts_choice = QtW.QComboBox()
        self._ts_choice.currentTextChanged.connect(self._ts_choice_changed)
        layout.addWidget(self._ts_choice)

    def on_job_updated(self, job_dir: _job.MotionCorrectionJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).name == "mask.mrc":
            self.initialize(job_dir)

    def initialize(self, job_dir: _job.MotionCorrectionJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        choices = [
            p.tomo_tilt_series_star_file.stem
            for p in job_dir.iter_corrected_tilt_series()
        ]
        self._ts_choice.clear()
        self._ts_choice.addItems(choices)
        self._viewer.auto_fit()

    def _ts_choice_changed(self, text: str):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        if job_dir is None:
            return

        info = job_dir.corrected_tilt_series(text)
        ts_view = info.read_tilt_series(job_dir.path)
        self._viewer.set_array_view(ts_view)
