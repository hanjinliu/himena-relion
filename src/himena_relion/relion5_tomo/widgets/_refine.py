from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore
from himena_relion._widgets import JobWidgetBase, Q3DViewer, register_job
from himena_relion import _job


@register_job(_job.Refine3DJobDirectory)
class QRefine3DViewer(QtW.QScrollArea, JobWidgetBase):
    def __init__(self):
        super().__init__()
        self._inner = QtW.QWidget()
        self.setWidget(self._inner)
        self.setWidgetResizable(True)
        layout = QtW.QVBoxLayout(self._inner)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self._viewer = Q3DViewer()
        self._viewer.setFixedHeight(240)
        self._class_choice = QtW.QSpinBox()
        self._iter_choice = QtW.QSpinBox()
        layout.addWidget(self._viewer)
        layout.addWidget(self._class_choice)
        layout.addWidget(self._iter_choice)
        self._index_start = 1

    def on_job_updated(self, job_dir: _job.Refine3DJobDirectory, path: str):
        """Handle changes to the job directory."""
        self.initialize(job_dir)

    def initialize(self, job_dir: _job.Refine3DJobDirectory):
        """Initialize the viewer with the job directory."""
        nclasses = job_dir.num_classes()
        if nclasses == 0:
            return
        niters = job_dir.num_iters()
        self._class_choice.setRange(1, nclasses)
        self._iter_choice.setRange(0, niters - 1)

        res = job_dir.get_result(self._iter_choice.value())
        map_refined = res.refined_map(self._class_choice.value() - self._index_start)
        self._viewer.set_image(map_refined)
