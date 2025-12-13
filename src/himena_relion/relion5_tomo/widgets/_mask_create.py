from __future__ import annotations
from pathlib import Path
import logging
from himena_relion._widgets import QJobScrollArea, Q3DViewer, register_job
from himena_relion import _job

_LOGGER = logging.getLogger(__name__)


@register_job(_job.MaskCreateJobDirectory)
class QMaskCreateViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._viewer = Q3DViewer()
        self._viewer.setMaximumHeight(480)
        self._layout.addWidget(self._viewer)

    def on_job_updated(self, job_dir: _job.MaskCreateJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).name == "mask.mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_id)

    def initialize(self, job_dir: _job.MaskCreateJobDirectory):
        """Initialize the viewer with the job directory."""
        mask = job_dir.mask_mrc()
        self._viewer.set_image(mask)
        self._viewer.auto_threshold(0.5)
        self._viewer.auto_fit()
