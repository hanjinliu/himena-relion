from __future__ import annotations

from qtpy import QtWidgets as QtW
from himena_relion._job import JobDirectory


class QJobEdit(QtW.QWidget):
    def __init__(self):
        super().__init__()
        # layout = QtW.QVBoxLayout(self)

    def update_by_job(self, job_dir: JobDirectory):
        """Update the widget based on the job directory."""
        # TODO: pick pre-defined signature from type_label
        bound = job_dir.to_bound_arguments()
        bound.signature
