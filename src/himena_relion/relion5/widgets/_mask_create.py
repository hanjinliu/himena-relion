from __future__ import annotations
from pathlib import Path
import logging
import numpy as np
import mrcfile
from numpy.typing import NDArray
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    spacer_widget,
)
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job("relion.maskcreate")
class QMaskCreateViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._viewer = Q3DViewer()
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(spacer_widget())

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).name == "mask.mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        mask = mask_mrc(job_dir)
        self._viewer.set_image(mask, update_now=False)
        self._viewer.auto_threshold(0.5, update_now=False)
        self._viewer.auto_fit()


def mask_mrc(job_dir: _job_dir.JobDirectory) -> NDArray[np.floating] | None:
    """Return the mask MRC file."""
    mask_path = job_dir.path / "mask.mrc"
    try:
        with mrcfile.open(mask_path, mode="r") as mrc:
            return mrc.data
    except Exception:
        return None
