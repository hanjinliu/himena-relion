from __future__ import annotations
from pathlib import Path
import logging
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    spacer_widget,
)
from himena_relion import _job

_LOGGER = logging.getLogger(__name__)


@register_job(_job.MaskCreateJobDirectory)
class QMaskCreateViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._viewer = Q3DViewer()
        self._viewer.setMaximumSize(400, 400)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(spacer_widget())

    def on_job_updated(self, job_dir: _job.MaskCreateJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).name == "mask.mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_id)

    def initialize(self, job_dir: _job.MaskCreateJobDirectory):
        """Initialize the viewer with the job directory."""
        mask = job_dir.mask_mrc()
        self._viewer.set_image(mask, update_now=False)
        self._viewer.auto_threshold(0.5, update_now=False)
        self._viewer.auto_fit()
