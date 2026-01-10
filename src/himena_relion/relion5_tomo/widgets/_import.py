from __future__ import annotations
from pathlib import Path
from qtpy import QtWidgets as QtW
import logging
from superqt.utils import thread_worker
from himena_relion._image_readers import ArrayFilteredView
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    Q2DFilterWidget,
    register_job,
    QMicrographListWidget,
)
from himena_relion import _job_dir
from himena_relion.schemas import TSModel, TSGroupModel

_LOGGER = logging.getLogger(__name__)


@register_job("relion.importtomo", is_tomo=True)
def import_tilt_series_viewer(job_dir: _job_dir.JobDirectory):
    if job_dir.get_job_param("do_coords") == "Yes":
        return QJobScrollArea()
    return QImportTiltSeriesViewer(job_dir)


class QImportTiltSeriesViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir

        self._viewer = Q2DViewer(zlabel="Tilt index")
        self._viewer.setMinimumHeight(420)
        self._filter_widget = Q2DFilterWidget(bin_default=8, lowpass_default=30)
        self._ts_list = QMicrographListWidget(
            ["Movie Name", "Optics Group", "Pixel Size (A)"]
        )
        self._ts_list.current_changed.connect(self._ts_choice_changed)
        self._layout.addWidget(QtW.QLabel("<b>Imported tilt series</b>"))
        self._layout.addWidget(self._ts_list)
        self._layout.addWidget(self._filter_widget)
        self._layout.addWidget(self._viewer)
        self._filter_widget.value_changed.connect(self._filter_param_changed)
        self._binsize_old = -1

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_"):
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        tilt_series_star_path = job_dir.path / "tilt_series.star"
        if not tilt_series_star_path.exists():
            return

        ts_group = TSGroupModel.validate_file(tilt_series_star_path)
        if ts_group.optics_group_name is None:
            optics_group_name = ["--"] * len(ts_group.tomo_name)
        else:
            optics_group_name = ts_group.optics_group_name
        choices: list[tuple[str, str, str]] = []
        for tomo_name, opt, pix in zip(
            ts_group.tomo_name,
            optics_group_name,
            ts_group.original_pixel_size,
        ):
            choices.append((tomo_name, opt, str(round(pix, 3))))
        choices.sort(key=lambda x: x[0])
        self._ts_list.set_choices(choices)

    def _ts_choice_changed(self, texts: tuple[str, ...]):
        """Handle changes to the selected tilt series."""
        if not texts:
            self._viewer.clear()
            return
        tomo_name = texts[0]
        ts_path = self._job_dir.path / "tilt_series" / f"{tomo_name}.star"
        if not ts_path.exists():
            self._viewer.clear()
            return
        ts_model = TSModel.validate_file(ts_path)
        movie_paths = ts_model.ts_movie_paths_sorted()
        self.window_closed_callback()
        self._worker = self._uncompress_and_read_image(movie_paths)
        self._start_worker()

    def _on_movie_loaded(self, movie_view: ArrayFilteredView | None):
        if movie_view is None:
            return self._viewer.clear()
        self._viewer.set_array_view(
            movie_view.with_filter(self._filter_widget.apply),
            clim=self._viewer._last_clim,
        )
        self._viewer._auto_contrast()

    @thread_worker
    def _uncompress_and_read_image(self, movie_paths: list[Path]):
        """If the movie is LZW-TIFF, uncompress it, then read it."""
        if len(movie_paths) == 0:
            yield self._on_movie_loaded, None
        elif movie_paths[0].suffix == ".mrc":
            yield self._on_movie_loaded, ArrayFilteredView.from_mrcs(movie_paths)
        else:
            yield self._on_movie_loaded, ArrayFilteredView.from_tif_movies(movie_paths)

    def _filter_param_changed(self):
        """Handle changes to filter parameters."""
        self._viewer.redraw()
        new_binsize = self._filter_widget.bin_factor()
        if self._binsize_old != new_binsize:
            self._binsize_old = new_binsize
            self._viewer.auto_fit()
