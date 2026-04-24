from __future__ import annotations
from pathlib import Path
import logging
import mrcfile
import numpy as np
from qtpy import QtWidgets as QtW, QtCore
from starfile_rs import read_star
from himena_relion._widgets import Q2DViewer, Q2DFilterWidget, QMicrographListWidget
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


class QAutoExcludeTiltsViewer(QtW.QWidget):
    def __init__(self, job_dir: _job_dir.ExternalJobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = QtW.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self._viewer = Q2DViewer()
        self._viewer.setMaximumHeight(480)
        self._filter_widget = Q2DFilterWidget(bin_default=8, lowpass_default=30)
        self._mic_choice = QMicrographListWidget(["Micrograph"])
        self._mic_choice.current_changed.connect(self._mic_changed)
        layout.addWidget(QtW.QLabel("<b>Tomogram Z slice with fiducials</b>"))
        layout.addWidget(self._mic_choice)
        layout.addWidget(self._viewer)
        self.initialize(job_dir)

    def on_job_updated(self, job_dir: _job_dir.ExternalJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).name == "excluded_tilts.star":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.ExternalJobDirectory):
        """Initialize the viewer with the job directory."""
        star_path = job_dir.path / "excluded_tilts.star"
        if not star_path.exists():
            return self._clear_contents()
        df = read_star(star_path).first().trust_loop().to_polars()
        if df.height == 0:
            return self._clear_contents()
        self._mic_choice.set_choices([(mic,) for mic in df["rlnMicrographName"]])

    def _mic_changed(self, texts: tuple[str]):
        """Handle changes to the selected micrograph."""
        mic_name = texts[0]
        path = self._job_dir.resolve_path(mic_name)
        with mrcfile.open(path) as mrc:
            img = np.asarray(mrc.data)
        if img.ndim == 3:
            img = img[img.shape[0] // 2]
        assert img.ndim == 2
        img_filt = self._filter_widget.apply(img)

        self._viewer.set_array_view(img_filt)

    def _clear_contents(self):
        self._viewer.clear()
        self._mic_choice.set_choices([])
