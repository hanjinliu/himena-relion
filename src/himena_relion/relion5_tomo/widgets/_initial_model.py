from __future__ import annotations

import logging
from pathlib import Path
from qtpy import QtWidgets as QtW
from himena_relion._widgets import QJobScrollArea, Q3DViewer, register_job, QIntWidget
from himena_relion import _job

_LOGGER = logging.getLogger(__name__)


@register_job(_job.InitialModel3DJobDirectory)
class QInitialModelViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        layout = self._layout
        self._viewer = Q3DViewer()
        self._viewer.setFixedSize(300, 300)

        self._class_choice = QIntWidget("Class", label_width=50)
        self._iter_choice = QIntWidget("Iteration", label_width=60)
        self._class_choice.setMinimum(1)
        self._iter_choice.setMinimum(0)
        layout.addWidget(self._viewer)
        hor_layout = QtW.QHBoxLayout()
        hor_layout.addWidget(self._iter_choice)
        hor_layout.addWidget(self._class_choice)
        hor_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(hor_layout)
        self._iter_choice.valueChanged.connect(self._on_iter_changed)
        self._class_choice.valueChanged.connect(self._on_class_changed)
        self._index_start = 1
        self._iter_current_value = 0
        self._job_dir: _job.InitialModel3DJobDirectory | None = None

    def on_job_updated(self, job_dir: _job.InitialModel3DJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", self._job_dir.job_id)

    def initialize(self, job_dir: _job.InitialModel3DJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        nclasses = job_dir.num_classes()
        if nclasses == 0:
            return
        niter_list = job_dir.niter_list()
        _LOGGER.info("Job with %s classes and %s iterations", nclasses, max(niter_list))
        self._class_choice.setMaximum(nclasses)
        self._iter_choice.setMaximum(max(niter_list + [0]))
        self._iter_choice.setValue(self._iter_choice.maximum())
        self._on_iter_changed(self._iter_choice.value())
        self._viewer.auto_threshold()
        self._viewer.auto_fit()

    def _on_iter_changed(self, value: int):
        niter_list = self._job_dir.niter_list()
        if value in niter_list:
            self._update_for_value(value, self._class_choice.value())
            self._iter_current_value = value
        else:
            if value > self._iter_current_value:
                next_iters = [n for n in niter_list if n > self._iter_current_value]
                if next_iters:
                    nearest_iter = min(next_iters)
                else:
                    nearest_iter = max(niter_list)
            else:
                prev_iters = [n for n in niter_list if n < self._iter_current_value]
                if prev_iters:
                    nearest_iter = max(prev_iters)
                else:
                    nearest_iter = min(niter_list)
            self._iter_choice.setValue(nearest_iter)

    def _on_class_changed(self, value: int):
        self._update_for_value(self._iter_choice.value(), value)

    def _update_for_value(self, niter: int, class_id: int):
        res = self._job_dir.get_result(niter)
        map0 = res.class_map(class_id - self._index_start)
        self._viewer.set_image(map0)
