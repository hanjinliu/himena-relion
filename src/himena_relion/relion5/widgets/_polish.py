from __future__ import annotations
from pathlib import Path
from qtpy import QtWidgets as QtW
import logging
from himena_relion._widgets import (
    QJobScrollArea,
    register_job,
)
from himena_relion import _job_dir


_LOGGER = logging.getLogger(__name__)


@register_job("relion.polish.train")
class QPolishTrainViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._text_edit = QtW.QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFixedSize(300, 200)
        self._layout.addWidget(self._text_edit)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith(("RELION_JOB_", "opt_params")):
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        txt_path = job_dir.path / "opt_params_all_groups.txt"
        if not txt_path.exists():
            return
        vals = txt_path.read_text().split(" ")
        sigma_vel = vals[0].strip()
        sigma_div = vals[1].strip()
        sigma_acc = vals[2].strip()

        text = (
            f"Sigma for velocity: <b>{sigma_vel}</b> (A/dose)<br>"
            f"Sigma for divergence <b>{sigma_div}</b> (A)<br>"
            f"Sigma for acceleration <b>{sigma_acc}</b> (A/dose)<br>"
        )
        self._text_edit.setHtml(text)
