from __future__ import annotations
from pathlib import Path
from himena import StandardType, WidgetDataModel
import polars as pl
from qtpy import QtWidgets as QtW
import numpy as np
from numpy.typing import NDArray
import logging
from starfile_rs import read_star
from superqt.utils import thread_worker
from himena.standards import plotting as hplt
from himena_relion._widgets import (
    QJobScrollArea,
    register_job,
    Q2DViewer,
    QMicrographListWidget,
    QPlotCanvas,
    Q2DFilterWidget,
)
from himena_relion._widgets._vispy import MotionPath
from himena_relion import _job_dir
from himena_relion.schemas import MicrographsStarModel, CoordsModel
from himena_relion._image_readers import ArrayFilteredView


_LOGGER = logging.getLogger(__name__)


@register_job("relion.polish.train")
class QPolishTrainViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._text_edit = QtW.QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFixedSize(300, 200)
        self._layout.addWidget(self._text_edit)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith(("RELION_JOB_", "opt_params")):
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        txt_path = job_dir.path / "opt_params_all_groups.txt"
        if not txt_path.exists():
            return
        vals = txt_path.read_text().split(" ")
        sigma_vel = vals[0].strip()
        sigma_div = vals[1].strip()
        sigma_acc = vals[2].strip()

        text = (
            f"Sigma for velocity: <b>{sigma_vel}</b> (A/dose)<br>"
            f"Sigma for divergence <b>{sigma_div}</b> (A)<br>"
            f"Sigma for acceleration <b>{sigma_acc}</b> (A/dose)<br>"
        )
        self._text_edit.setHtml(text)


@register_job("relion.polish")
class QPolishViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._bfactor_plot = QPlotCanvas(self)
        self._scalefactor_plot = QPlotCanvas(self)
        self._viewer = Q2DViewer(zlabel="")
        self._viewer.setMinimumHeight(480)
        self._mic_list = QMicrographListWidget(["Micrograph", "Path", "Tracks"])
        self._mic_list.setFixedHeight(130)
        self._mic_list.current_changed.connect(self._mic_changed)
        self._mic_list.setColumnHidden(1, True)
        self._filter_widget = Q2DFilterWidget(bin_default=8, lowpass_default=30)
        layout.addWidget(QtW.QLabel("<b>Bayesian Polish Tracks (scaled by 8)</b>"))
        layout.addWidget(self._mic_list)
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._viewer)
        layout.addWidget(QtW.QLabel("<b>Per-frame B-factor Used for Sharpening</b>"))
        layout.addWidget(self._bfactor_plot)
        layout.addWidget(QtW.QLabel("<b>Per-frame Scale Factor</b>"))
        layout.addWidget(self._scalefactor_plot)
        self._filter_widget.value_changed.connect(self._filter_param_changed)
        self._binsize_old = -1
        self._motion_visual = MotionPath(
            antialias=True, parent=self._viewer._canvas._viewbox.scene
        )
        self._motion_visual.set_gl_state(depth_test=False)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.name.endswith(
            ("_shiny.star", "_tracks.star")
        ):
            self._process_update()
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def _mic_changed(self, row: tuple[str, str, str]):
        """Handle changes to selected micrograph."""
        mic_path = Path(row[1])
        track_path = self._job_dir.resolve_path(row[2])
        shiny_path = track_path.with_name(f"{mic_path.stem}_shiny.star")
        if mic_path.exists() and track_path.exists() and shiny_path.exists():
            self.window_closed_callback()
            self._worker = self._read_items(mic_path, track_path, shiny_path)
            self._start_worker()

    @thread_worker
    def _read_items(self, mic_path: Path, track_path: Path, shiny_path: Path):
        movie_view = ArrayFilteredView.from_mrc(mic_path)
        self._filter_widget.set_image_scale(movie_view.get_scale())
        bin_factor = self._filter_widget.bin_factor()
        zoom = 8
        scale = movie_view.get_scale()
        yield self._update_micrograph, movie_view.with_filter(self._filter_widget.apply)

        star_track = read_star(track_path)
        motions = [t.to_polars().to_numpy() for t in star_track.values()]
        motions = motions[1:]  # first one is data_general
        model_shiny = CoordsModel.validate_file(shiny_path)
        if len(motions) != model_shiny.x.size:
            _LOGGER.warning(
                "Number of motion tracks does not match number of particles"
            )
            return
        pos_shiny = np.stack([model_shiny.y, model_shiny.x], axis=1) / bin_factor
        motion_scale = 1 / scale / bin_factor * zoom
        tracks = [
            (motions[i] * motion_scale + pos_shiny[i][np.newaxis])[:, ::-1]
            for i in range(len(motions))
        ]
        yield self._update_tracks, (tracks, pos_shiny)
        if (bfactor_star := self._job_dir.path / "bfactors.star").exists():
            star_bfactor = read_star(bfactor_star).first().to_polars()
            yield self._update_plots, star_bfactor

    def _update_micrograph(self, mic_view: ArrayFilteredView):
        self._viewer.set_array_view(mic_view, clim=self._viewer._last_clim)
        self._viewer._auto_contrast()

    def _update_tracks(
        self, data: tuple[list[NDArray[np.float32]], NDArray[np.float32]]
    ):
        motion, points = data
        self._viewer.set_points(points, size=10)
        self._viewer.redraw()
        self._motion_visual.set_data(motion)

    def _update_plots(self, star: pl.DataFrame):
        x = star["rlnMovieFrameNumber"]
        y1 = star["rlnBfactorUsedForSharpening"]
        y2 = star["rlnFittedInterceptGuinierPlot"]
        with self._bfactor_plot._plot_style():
            fig = hplt.figure()
            fig.plot(x, y1)
            fig.x.label = "Movie Frame Number"
            fig.y.label = "B-factor (A^2)"
            self._bfactor_plot.update_model(
                WidgetDataModel(value=fig, type=StandardType.PLOT)
            )
            self._bfactor_plot.tight_layout()
            fig = hplt.figure()
            fig.plot(x, y2)
            fig.x.label = "Movie Frame Number"
            fig.y.label = "Scale Factors"
            self._scalefactor_plot.update_model(
                WidgetDataModel(value=fig, type=StandardType.PLOT)
            )
            self._scalefactor_plot.tight_layout()

    def _filter_param_changed(self):
        """Handle changes to filter parameters."""
        new_binsize = self._filter_widget.bin_factor()
        self._mic_changed(self._mic_list.current_tuple())
        if self._binsize_old != new_binsize:
            self._binsize_old = new_binsize
            self._viewer.auto_fit()

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        choices = []
        # usually, fn_mic="MotionCorr/job002/corrected_micrographs.star "
        fn_mic = self._job_dir.get_job_param("fn_mic")
        mic_path = self._job_dir.resolve_path(fn_mic)
        mic_model = MicrographsStarModel.validate_file(mic_path)
        for p in mic_model.micrographs.mic_name:
            path = self._job_dir.resolve_path(p)
            # path = "MotionCorr/job002/Movies/<name>.mrc"
            track_path = (
                self._job_dir.path / path.parent.name / f"{path.stem}_tracks.star"
            )
            if track_path.exists():
                track_rel = self._job_dir.make_relative_path(track_path)
                choices.append((path.name, path.as_posix(), track_rel.as_posix()))
        self._mic_list.set_choices(choices)
        if len(choices) == 0:
            self._viewer.clear()
