from __future__ import annotations
from pathlib import Path
import logging
import numpy as np
import pandas as pd
from qtpy import QtWidgets as QtW
import starfile
from himena_relion._image_readers._array import ArrayFilteredView
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    QPlotCanvas,
    register_job,
)
from himena_relion import _job

_LOGGER = logging.getLogger(__name__)


@register_job(_job.CtfCorrectionJobDirectory)
class QCtfFindViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job.CtfCorrectionJobDirectory = None
        layout = self._layout
        self._defocus_canvas = QPlotCanvas(self)
        self._defocus_canvas.setFixedSize(360, 120)
        self._astigmatism_canvas = QPlotCanvas(self)
        self._astigmatism_canvas.setFixedSize(360, 120)
        self._defocus_angle_canvas = QPlotCanvas(self)
        self._defocus_angle_canvas.setFixedSize(360, 120)
        self._max_resolution_canvas = QPlotCanvas(self)
        self._max_resolution_canvas.setFixedSize(360, 120)

        self._viewer = Q2DViewer(zlabel="Tilt index")
        self._ts_choice = QtW.QComboBox()
        self._ts_choice.currentTextChanged.connect(self._ts_choice_changed)
        layout.addWidget(self._ts_choice)
        layout.addWidget(QtW.QLabel("<b>Defocus</b>"))
        layout.addWidget(self._defocus_canvas)
        layout.addWidget(QtW.QLabel("<b>Astigmatism</b>"))
        layout.addWidget(self._astigmatism_canvas)
        layout.addWidget(QtW.QLabel("<b>Defocus angle</b>"))
        layout.addWidget(self._defocus_angle_canvas)
        layout.addWidget(QtW.QLabel("<b>Max resolution</b>"))
        layout.addWidget(self._max_resolution_canvas)
        layout.addWidget(QtW.QLabel("<b>CTF spectra</b>"))
        layout.addWidget(self._viewer)

    def on_job_updated(self, job_dir: _job.CtfCorrectionJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".ctf":
            self._process_update()
            _LOGGER.debug("%s Updated", self._job_dir.job_id)

    def initialize(self, job_dir: _job.CtfCorrectionJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        choices = [p.stem for p in self._job_dir.iter_tilt_series_path()]
        index = self._ts_choice.currentIndex()
        self._ts_choice.clear()
        self._ts_choice.addItems(choices)
        if choices:
            self._ts_choice.setCurrentIndex(
                min(index if index >= 0 else 0, len(choices) - 1)
            )
        else:
            # clear everything
            self._defocus_canvas.clear()
            self._astigmatism_canvas.clear()
            self._defocus_angle_canvas.clear()
            self._max_resolution_canvas.clear()
            self._viewer.clear()

    def _ts_choice_changed(self, text: str):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        if job_dir is None:
            return
        for path in job_dir.iter_tilt_series_path():
            if path.stem == text:
                break
        else:
            return
        df = starfile.read(path)
        assert isinstance(df, pd.DataFrame)
        rln_dir = job_dir.relion_project_dir
        paths = [rln_dir / p for p in df["rlnCtfImage"]]
        if "rlnTomoNominalStageTiltAngle" in df:
            tilt_angles = df["rlnTomoNominalStageTiltAngle"]
            order = np.argsort(tilt_angles)
            paths = [paths[i] for i in order]
            df = df.iloc[order].reset_index(drop=True)
        ts_view = ArrayFilteredView.from_mrcs(paths)

        self._defocus_canvas.plot_defocus(df)
        self._astigmatism_canvas.plot_ctf_astigmatism(df)
        self._defocus_angle_canvas.plot_ctf_defocus_angle(df)
        self._max_resolution_canvas.plot_ctf_max_resolution(df)
        self._viewer.set_array_view(ts_view)


@register_job(_job.CtfRefineTomoJobDirectory)
class QCtfRefineTomoViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job.CtfRefineTomoJobDirectory = None
        layout = self._layout
        self._defocus_canvas = QPlotCanvas(self)
        self._defocus_canvas.setFixedSize(360, 160)
        self._ctf_scale_canvas = QPlotCanvas(self)
        self._ctf_scale_canvas.setFixedSize(360, 160)
        self._ts_choice = QtW.QComboBox()
        self._ts_choice.currentTextChanged.connect(self._ts_choice_changed)
        layout.addWidget(self._ts_choice)
        layout.addWidget(QtW.QLabel("<b>Defocus</b>"))
        layout.addWidget(self._defocus_canvas)
        layout.addWidget(QtW.QLabel("<b>CTF Scale Factor</b>"))
        layout.addWidget(self._ctf_scale_canvas)

    def initialize(self, job_dir: _job.CtfRefineTomoJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        self._process_update()

    def _process_update(self):
        choices = [p.stem for p in self._job_dir.iter_tilt_series_path()]
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
        for ts_path in job_dir.iter_tilt_series_path():
            if ts_path.stem == text:
                df = starfile.read(ts_path)
                self._defocus_canvas.plot_defocus(df)
                self._ctf_scale_canvas.plot_ctf_scale(df)
                break
