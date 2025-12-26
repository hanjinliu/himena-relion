from __future__ import annotations
from pathlib import Path
import logging
from himena_relion._widgets import QJobScrollArea, register_job
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job(_job_dir.ImportJobDirectory)
class QImportTiltSeriesViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()

    def on_job_updated(self, job_dir: _job_dir.ImportJobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix not in [
            ".out",
            ".err",
            ".star",
        ]:
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_id)

    def initialize(self, job_dir: _job_dir.ImportJobDirectory):
        """Initialize the viewer with the job directory."""
        ...
