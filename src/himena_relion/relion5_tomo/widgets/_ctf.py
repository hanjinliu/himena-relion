from __future__ import annotations
from pathlib import Path

from qtpy import QtWidgets as QtW
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    QPlotCanvas,
    register_job,
)
from himena_relion import _job


@register_job(_job.CtfCorrectionJobDirectory)
class QCtfFindViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job.CtfCorrectionJobDirectory = None
        layout = self._layout
        self._defocus_canvas = QPlotCanvas()
        self._defocus_canvas.setFixedSize(360, 120)
        self._viewer = Q2DViewer(zlabel="Tilt index")
        self._ts_choice = QtW.QComboBox()
        self._ts_choice.currentTextChanged.connect(self._ts_choice_changed)
        layout.addWidget(self._ts_choice)
        layout.addWidget(QtW.QLabel("<b>Defocus</b>"))
        layout.addWidget(self._defocus_canvas)
        layout.addWidget(QtW.QLabel("<b>CTF spectra</b>"))
        layout.addWidget(self._viewer)

    def on_job_updated(self, job_dir: _job.CtfCorrectionJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".ctf":
            self._process_update(job_dir)

    def initialize(self, job_dir: _job.CtfCorrectionJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        choices = [
            p.tomo_tilt_series_star_file.stem for p in self._job_dir.iter_tilt_series()
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
        for info in job_dir.iter_tilt_series():
            if info.tomo_tilt_series_star_file.stem == text:
                break
        else:
            return
        ts_view = info.read_ctf_series(job_dir.relion_project_dir)
        self._defocus_canvas.plot_defocus(ts_view.dataframe)
        self._viewer.set_array_view(ts_view)
