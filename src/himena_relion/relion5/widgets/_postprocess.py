from __future__ import annotations
from pathlib import Path
import logging
import mrcfile
from qtpy import QtWidgets as QtW, QtCore
from superqt import QToggleSwitch
from starfile_rs import read_star
from himena_relion._utils import wait_for_file
from himena_relion._widgets import (
    QJobScrollArea,
    QPlotCanvas,
    register_job,
    Q3DViewer,
    spacer_widget,
    QNumParticlesLabel,
)
from himena_relion import _job_dir
from himena_relion._widgets._shared.resizer import QResizer

_LOGGER = logging.getLogger(__name__)


@register_job("relion.postprocess")
class QPostProcessViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        max_width = 440
        self._viewer = Q3DViewer()
        self._resizer = QResizer(self._viewer)
        self._resizer.setMaximumWidth(max_width)
        self._use_mask = QToggleSwitch("Show masked map")
        self._use_mask.setChecked(True)
        self._num_particles_label = QNumParticlesLabel()
        self._canvas = QPlotCanvas(self)
        self._canvas.setMaximumSize(max_width, 280)
        self._canvas.setMinimumSize(340, 200)
        self._layout.setSpacing(0)
        self._layout.addWidget(QtW.QLabel("<b>&#9679; Sharpened Map</b>"))
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(self._resizer)
        hor = QtW.QWidget()
        hor.setMaximumWidth(max_width)
        h_layout = QtW.QHBoxLayout(hor)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.addWidget(self._use_mask)
        h_layout.addWidget(
            self._num_particles_label, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        self._layout.addWidget(hor)
        self._layout.addSpacing(5)
        self._layout.addWidget(QtW.QLabel("<b>&#9679; Fourier Shell Correlation</b>"))
        self._layout.addWidget(self._canvas)
        self._layout.addWidget(spacer_widget())
        self._job_dir = job_dir
        self._use_mask.toggled.connect(self._on_use_mask_toggled)

        self._current_map_path = None

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).name in ["postprocess_masked.mrc", "postprocess.mrc"]:
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        # show map
        if self._use_mask.isChecked():
            mrc_path = job_dir.path / "postprocess_masked.mrc"
        else:
            mrc_path = job_dir.path / "postprocess.mrc"
        if wait_for_file(mrc_path):
            with mrcfile.open(mrc_path, mode="r") as mrc:
                img = mrc.data
            self._viewer.set_image(img, update_now=False)
            self._viewer.auto_threshold(update_now=False)
            self._viewer.auto_fit()
            self._current_map_path = mrc_path

            # look for the particle number
            if not self._num_particles_label.num_known():
                num = _job_dir.try_get_particle_number(self._job_dir)
                self._num_particles_label.set_number(num)
        else:
            self._viewer.set_image(None)
            self._current_map_path = None

        # show FSC
        if wait_for_file(starpath := job_dir.path / "postprocess.star", delay=0.02):
            star_postprocess = read_star(starpath)
            self._canvas.plot_fsc_postprocess(
                star_postprocess["fsc"].trust_loop().to_polars(),
                star_postprocess["general"].trust_single().to_dict(),
            )

    def _on_use_mask_toggled(self, *_):
        """Handle toggling between masked and unmasked maps."""
        self.initialize(self._job_dir)

    def widget_added_callback(self):
        self._canvas.widget_added_callback()
