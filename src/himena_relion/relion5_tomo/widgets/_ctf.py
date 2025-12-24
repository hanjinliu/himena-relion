from __future__ import annotations
from pathlib import Path
import logging
from typing import Any, Callable
import numpy as np
from qtpy import QtWidgets as QtW
from superqt.utils import thread_worker, GeneratorWorker
from starfile_rs import read_star
from himena_relion._image_readers._array import ArrayFilteredView
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    QPlotCanvas,
    register_job,
)
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job(_job_dir.CtfCorrectionJobDirectory)
class QCtfFindViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job_dir.CtfCorrectionJobDirectory = None
        layout = self._layout
        self._defocus_canvas = QPlotCanvas(self)
        self._defocus_canvas.setFixedSize(360, 145)
        self._astigmatism_canvas = QPlotCanvas(self)
        self._astigmatism_canvas.setFixedSize(360, 145)
        self._defocus_angle_canvas = QPlotCanvas(self)
        self._defocus_angle_canvas.setFixedSize(360, 145)
        self._max_resolution_canvas = QPlotCanvas(self)
        self._max_resolution_canvas.setFixedSize(360, 145)

        self._viewer = Q2DViewer(zlabel="Tilt index")
        self._worker: GeneratorWorker | None = None
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

    def on_job_updated(self, job_dir: _job_dir.CtfCorrectionJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".ctf":
            self._process_update()
            _LOGGER.debug("%s Updated", self._job_dir.job_id)

    def initialize(self, job_dir: _job_dir.CtfCorrectionJobDirectory):
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

        self.widget_closed_callback()
        self._worker = self._prep_data_to_plot(job_dir, path)
        self._worker.yielded.connect(self._on_data_ready)
        self._worker.start()

    @thread_worker
    def _prep_data_to_plot(
        self,
        job_dir: _job_dir.CtfCorrectionJobDirectory,
        path: Path,
    ):
        df = read_star(path).first().trust_loop().to_pandas()
        rln_dir = job_dir.relion_project_dir
        paths = [rln_dir / p for p in df["rlnCtfImage"]]
        if "rlnTomoNominalStageTiltAngle" in df:
            tilt_angles = df["rlnTomoNominalStageTiltAngle"]
            order = np.argsort(tilt_angles)
            paths = [paths[i] for i in order]
            df = df.iloc[order].reset_index(drop=True)
        ts_view = ArrayFilteredView.from_mrcs(paths)

        yield self._defocus_canvas.plot_defocus, df
        yield self._astigmatism_canvas.plot_ctf_astigmatism, df
        yield self._defocus_angle_canvas.plot_ctf_defocus_angle, df
        yield self._max_resolution_canvas.plot_ctf_max_resolution, df
        yield self._viewer.set_array_view, ts_view

    def _on_data_ready(self, yielded: tuple[Callable, Any]):
        fn, df = yielded
        fn(df)

    def widget_added_callback(self):
        self._defocus_canvas.widget_added_callback()
        self._astigmatism_canvas.widget_added_callback()
        self._defocus_angle_canvas.widget_added_callback()
        self._max_resolution_canvas.widget_added_callback()

    def closeEvent(self, a0):
        self.widget_closed_callback()
        return super().closeEvent(a0)

    def widget_closed_callback(self):
        if self._worker is not None:
            self._worker.quit()
            self._worker = None


@register_job(_job_dir.CtfRefineTomoJobDirectory)
class QCtfRefineTomoViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job_dir.CtfRefineTomoJobDirectory = None
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

    def initialize(self, job_dir: _job_dir.CtfRefineTomoJobDirectory):
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
                df = read_star(ts_path).first().trust_loop().to_pandas()
                self._defocus_canvas.plot_defocus(df)
                self._ctf_scale_canvas.plot_ctf_scale(df)
                break

    def widget_added_callback(self):
        self._defocus_canvas.widget_added_callback()
        self._ctf_scale_canvas.widget_added_callback()
