from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable
from qtpy import QtWidgets as QtW
from superqt.utils import thread_worker
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    QIntWidget,
    QIntChoiceWidget,
    QNumParticlesLabel,
)
from himena_relion import _job_dir
from himena_relion.schemas import ModelStarModel

_LOGGER = logging.getLogger(__name__)


@register_job("relion.initialmodel")
@register_job("relion.initialmodel.tomo", is_tomo=True)
class QInitialModelViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.InitialModel3DJobDirectory):
        super().__init__()
        layout = self._layout
        self._viewer = Q3DViewer()

        self._class_choice = QIntWidget("Class", label_width=50)
        self._iter_choice = QIntChoiceWidget("Iteration", label_width=60)
        self._class_choice.setMinimum(1)
        self._iter_choice.setMinimum(0)
        self._num_particles_label = QNumParticlesLabel()
        layout.addWidget(self._viewer)
        layout.addWidget(self._num_particles_label)
        hor_layout = QtW.QHBoxLayout()
        hor_layout.addWidget(self._iter_choice)
        hor_layout.addWidget(self._class_choice)
        hor_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(hor_layout)
        self._iter_choice.current_changed.connect(self._on_iter_changed)
        self._class_choice.valueChanged.connect(self._on_class_changed)
        self._index_start = 1
        self._iter_current_value = 0
        self._job_dir = _job_dir.InitialModel3DJobDirectory(job_dir.path)

    def on_job_updated(self, job_dir: _job_dir.InitialModel3DJobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def initialize(self, job_dir: _job_dir.InitialModel3DJobDirectory):
        """Initialize the viewer with the job directory."""
        nclasses = self._job_dir.num_classes()
        if nclasses == 0:
            return
        niter_list = self._job_dir.niter_list()
        _LOGGER.info("Job with %s classes and %s iterations", nclasses, max(niter_list))
        self._class_choice.setMaximum(nclasses)
        self._iter_choice.set_choices(niter_list)
        self._iter_choice.setValue(self._iter_choice.maximum())
        self._on_iter_changed(self._iter_choice.value())
        self._viewer.auto_threshold()
        self._viewer.auto_fit()

    def _on_iter_changed(self, value: int):
        self._update_for_value(value, self._class_choice.value())

    def _on_class_changed(self, value: int):
        self._update_for_value(self._iter_choice.value(), value)

    def _update_for_value(self, niter: int, class_id: int = 1):
        if self._worker is not None and self._worker.is_running:
            self._worker.quit()
        self._worker = None
        self._worker = self._read_items(niter, class_id)
        self._worker.yielded.connect(self._on_yielded)
        self._worker.start()

    @thread_worker
    def _read_items(self, niter, class_id: int = 1):
        res = self._job_dir.get_result(niter)

        res = self._job_dir.get_result(niter)
        map0 = res.class_map(class_id - self._index_start)
        yield self._viewer.set_image, map0
        starpath = self._job_dir.path / f"run_it{niter:0>3}_model.star"
        try:
            model = ModelStarModel.validate_file(starpath)
            num_particles = model.groups.num_particles.sum()
        except Exception as e:
            num_particles = -1
            raise e
        yield self._num_particles_label.set_number, num_particles

    def _on_yielded(self, yielded: tuple[Callable, Any]):
        fn, args = yielded
        fn(args)
