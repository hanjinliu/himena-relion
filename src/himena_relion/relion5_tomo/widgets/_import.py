from __future__ import annotations
from pathlib import Path

from himena_relion._widgets import QJobScrollArea, register_job
from himena_relion import _job


@register_job(_job.ImportJobDirectory)
class QImportTiltSeriesViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()

    def on_job_updated(self, job_dir: _job.ImportJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix not in [".out", ".err", ".star"]:
            self.initialize(job_dir)

    def initialize(self, job_dir: _job.ImportJobDirectory):
        """Initialize the viewer with the job directory."""
        ...
