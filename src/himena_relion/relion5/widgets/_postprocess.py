from __future__ import annotations
from pathlib import Path
import logging
import mrcfile
from superqt import QToggleSwitch
from starfile_rs import read_star
from himena_relion._utils import wait_for_file
from himena_relion._widgets import (
    QJobScrollArea,
    QPlotCanvas,
    register_job,
    Q3DViewer,
    spacer_widget,
)
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job("relion.postprocess")
class QPostProcessViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._viewer = Q3DViewer()
        self._use_mask = QToggleSwitch("Show masked map")
        self._use_mask.setChecked(False)
        self._canvas = QPlotCanvas(self)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(self._use_mask)
        self._layout.addWidget(self._canvas)
        self._layout.addWidget(spacer_widget())
        self._job_dir = job_dir
        self._use_mask.toggled.connect(self._on_use_mask_toggled)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix not in [".out", ".err"]:
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
