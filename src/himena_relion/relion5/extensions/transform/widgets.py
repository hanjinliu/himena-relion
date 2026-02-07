from __future__ import annotations
from pathlib import Path
import logging
import numpy as np
import mrcfile
from qtpy import QtWidgets as QtW
from himena_relion._widgets import (
    Q3DViewer,
    spacer_widget,
)
from himena_relion import _job_dir
from . import _const as _c

_LOGGER = logging.getLogger(__name__)


class QShiftMapViewer(QtW.QWidget):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        self._viewer = Q3DViewer()
        layout.addWidget(self._viewer)
        layout.addWidget(spacer_widget())
        self.initialize(job_dir)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).name == _c.OUTPUT_MAP:
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        map_path = job_dir.path / _c.OUTPUT_MAP
        if map_path.exists():
            with mrcfile.open(map_path) as mrc:
                img = np.asarray(mrc.data, dtype=np.float32)
            self._viewer.set_image(img)
