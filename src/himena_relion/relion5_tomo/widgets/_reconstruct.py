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


@register_job(_job.ReconstructParticlesJobDirectory)
class QReconstructViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._viewer = Q3DViewer()
        self._viewer.setMaximumSize(400, 400)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(spacer_widget())

    def on_job_updated(self, job_dir: _job.ReconstructParticlesJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_id)

    def initialize(self, job_dir: _job.ReconstructParticlesJobDirectory):
        """Initialize the viewer with the job directory."""
        img = job_dir.merged_mrc()
        self._viewer.set_image(img, update_now=False)
        self._viewer.auto_threshold(update_now=False)
        self._viewer.auto_fit()
