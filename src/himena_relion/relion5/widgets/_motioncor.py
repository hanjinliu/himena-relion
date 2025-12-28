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
)
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job(_job_dir.MotionCorrJobDirectory)
@register_job(_job_dir.MotionCorrOwnJobDirectory)
def make_motion_corr_viewer(job_dir: _job_dir.MotionCorrBase):
    if job_dir.is_tomo():
        from himena_relion.relion5_tomo.widgets import _tilt_series

        return _tilt_series.QMotionCorrViewer(job_dir)
    return QMotionCorrViewer(job_dir)


class QMotionCorrViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.MotionCorrBase):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._viewer = Q2DViewer(zlabel="")
        self._mic_list = QtW.QListWidget()
        self._mic_list.setFixedHeight(180)
        self._mic_list.currentTextChanged.connect(self._param_changed)
        self._filter_widget = Q2DFilterWidget()
        layout.addWidget(QtW.QLabel("<b>Motion-corrected tilt series</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._viewer)
        layout.addWidget(self._mic_list)
        self._filter_widget.value_changed.connect(self._param_changed)
        self._binsize_old = -1

    def on_job_updated(self, job_dir: _job_dir.MotionCorrBase, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".mrc":
            self._process_update()
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def _mic_changed(self, text: str):
        """Handle changes to selected micrograph."""
        mic_path = self._job_dir.path / "Movies" / text
        movie_view = ArrayFilteredView.from_mrc(mic_path)
        self._viewer.set_array_view(movie_view.with_filter(self._filter_widget.apply))

    def _param_changed(self):
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
        choices = [p.stem for p in self._job_dir.iter_movies()]
        if choices:
            self._mic_list.clear()
            self._mic_list.addItems(choices)
