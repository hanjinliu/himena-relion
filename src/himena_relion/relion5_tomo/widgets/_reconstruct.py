from __future__ import annotations
from pathlib import Path

from himena_relion._widgets import QJobScrollArea, Q3DViewer, register_job
from himena_relion import _job


@register_job(_job.ReconstructParticlesJobDirectory)
class QReconstructViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._viewer = Q3DViewer()
        self._layout.addWidget(self._viewer)

    def on_job_updated(self, job_dir: _job.ReconstructParticlesJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".mrc":
            self.initialize(job_dir)

    def initialize(self, job_dir: _job.ReconstructParticlesJobDirectory):
        """Initialize the viewer with the job directory."""
        img = job_dir.merged_mrc()
        self._viewer.set_image(img)
        self._viewer.auto_threshold(0.5)
        self._viewer.auto_fit()
