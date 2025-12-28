from __future__ import annotations
from pathlib import Path
import logging
import mrcfile
import numpy as np
from numpy.typing import NDArray
import pandas as pd
from superqt import QToggleSwitch
from starfile_rs import read_star_block
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
        self._job_dir = job_dir
        img = map_mrc(job_dir, masked=self._use_mask.isChecked())
        if img is not None:
            self._viewer.set_image(img, update_now=False)
            self._viewer.auto_threshold(update_now=False)
            self._viewer.auto_fit()

        df_fsc = fsc_dataframe(job_dir)
        if df_fsc is not None:
            self._canvas.plot_fsc_postprocess(df_fsc)

    def _on_use_mask_toggled(self, *_):
        """Handle toggling between masked and unmasked maps."""
        self.initialize(self._job_dir)

    def widget_added_callback(self):
        self._canvas.widget_added_callback()


def map_mrc(
    self: _job_dir.JobDirectory, masked: bool = False
) -> NDArray[np.floating] | None:
    """Return the post-processed map MRC file."""
    name = "postprocess_masked.mrc" if masked else "postprocess.mrc"
    mrc_path = self.path / name
    if mrc_path.exists():
        with mrcfile.open(mrc_path, mode="r") as mrc:
            return mrc.data


def fsc_dataframe(self: _job_dir.JobDirectory) -> pd.DataFrame | None:
    """Return the FSC DataFrame."""
    star_path = self.path / "postprocess.star"
    if star_path.exists():
        return read_star_block(star_path, "fsc").trust_loop().to_pandas()
