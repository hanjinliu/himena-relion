from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore
from himena_relion._widgets import JobWidgetBase, Q3DViewer, register_job
from himena_relion import _job


@register_job(_job.InitialModel3DJobDirectory)
class QInitialModelViewer(QtW.QScrollArea, JobWidgetBase):
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
        self._iter_choice = QtW.QComboBox()
        layout.addWidget(self._viewer)
        layout.addWidget(self._iter_choice)
        self._index_start = 1

    def on_job_updated(self, job_dir: _job.InitialModel3DJobDirectory, path: str):
        """Handle changes to the job directory."""
        self.initialize(job_dir)

    def initialize(self, job_dir: _job.InitialModel3DJobDirectory):
        """Initialize the viewer with the job directory."""
        nclasses = job_dir.num_classes()
        if nclasses == 0:
            return
        niters = job_dir.niter_list()
        self._iter_choice.addItems([f"iter {i}" for i in niters])

        res = job_dir.get_result(niters[-1])
        for i in range(nclasses):
            viewer = Q3DViewer()
            map_refined = res.class_map(i)
            viewer.setFixedSize(QtCore.QSize(200, 200))
            viewer.set_image(map_refined)
