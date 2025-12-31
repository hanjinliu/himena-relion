from __future__ import annotations
from pathlib import Path
import logging
from qtpy import QtWidgets as QtW
from himena_relion._image_readers._array import ArrayFilteredView
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    Q2DFilterWidget,
    register_job,
    QMicrographListWidget,
)
from himena_relion.schemas import MoviesStarModel
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job("relion.import.movies", is_tomo=False)
class QImportMoviesViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._viewer = Q2DViewer(zlabel="")
        self._viewer.setMinimumHeight(480)
        self._mic_list = QMicrographListWidget(
            ["Movie Name", "Optics Group", "Pixel Size"]
        )
        self._mic_list.setFixedHeight(130)
        self._mic_list.current_changed.connect(self._mic_changed)
        self._filter_widget = Q2DFilterWidget()
        layout.addWidget(QtW.QLabel("<b>Imported-movies</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._viewer)
        layout.addWidget(self._mic_list)
        self._filter_widget.value_changed.connect(self._filter_param_changed)
        self._binsize_old = -1

    def on_job_updated(self, job_dir: _job_dir.MotionCorrBase, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.name == "movies.star":
            self._process_update()
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def _mic_changed(self, row: tuple[str, ...]):
        """Handle changes to selected micrograph."""
        movie_path = self._job_dir.resolve_path(row[0])

        movie_view = ArrayFilteredView.from_tif(movie_path)
        had_image = self._viewer.has_image
        self._filter_widget.set_image_scale(movie_view.get_scale())
        self._viewer.set_array_view(
            movie_view.with_filter(self._filter_widget.apply),
            clim=self._viewer._last_clim,
        )
        if not had_image:
            self._viewer._auto_contrast()

    def _filter_param_changed(self):
        """Handle changes to filter parameters."""
        self._viewer.redraw()
        new_binsize = self._filter_widget.bin_factor()
        if self._binsize_old != new_binsize:
            self._binsize_old = new_binsize
            self._viewer.auto_fit()

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        movies_star_path = self._job_dir.path / "movies.star"
        if not movies_star_path.exists():
            return
        mov = MoviesStarModel.validate_file(movies_star_path)
        optics_map = mov.optics.make_optics_map()
        choices = []
        for movie_name, opt_id in zip(mov.movies.movie_name, mov.movies.optics_group):
            if opt := optics_map.get(opt_id):
                choices.append(
                    [
                        movie_name,
                        opt.optics_group_name,
                        str(round(opt.mic_orig_pixel_size, 3)),
                    ]
                )
        self._mic_list.set_choices(choices)


@register_job("relion.motioncorr", is_tomo=False)
class QMotionCorrViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.MotionCorrBase):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._viewer = Q2DViewer(zlabel="")
        self._viewer.setMinimumHeight(480)
        self._mic_list = QMicrographListWidget()
        self._mic_list.setFixedHeight(130)
        self._mic_list.current_changed.connect(self._mic_changed)
        self._filter_widget = Q2DFilterWidget()
        layout.addWidget(QtW.QLabel("<b>Motion-corrected micrographs</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._viewer)
        layout.addWidget(self._mic_list)
        self._filter_widget.value_changed.connect(self._filter_param_changed)
        self._binsize_old = -1

    def on_job_updated(self, job_dir: _job_dir.MotionCorrBase, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".mrc":
            self._process_update()
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def _mic_changed(self, row: tuple[str]):
        """Handle changes to selected micrograph."""
        mic_path = self._job_dir.path / "Movies" / row[0]
        movie_view = ArrayFilteredView.from_mrc(mic_path)
        had_image = self._viewer.has_image
        self._filter_widget.set_image_scale(movie_view.get_scale())
        self._viewer.set_array_view(
            movie_view.with_filter(self._filter_widget.apply),
            clim=self._viewer._last_clim,
        )
        if not had_image:
            self._viewer._auto_contrast()

    def _filter_param_changed(self):
        """Handle changes to filter parameters."""
        self._viewer.redraw()
        new_binsize = self._filter_widget.bin_factor()
        if self._binsize_old != new_binsize:
            self._binsize_old = new_binsize
            self._viewer.auto_fit()

    def initialize(self, job_dir: _job_dir.MotionCorrBase):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir

        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        choices = [(p.name,) for p in self._job_dir.iter_movies()]
        self._mic_list.set_choices(choices)
