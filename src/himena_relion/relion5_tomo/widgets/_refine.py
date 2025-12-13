from __future__ import annotations
from pathlib import Path
import logging
from qtpy import QtWidgets as QtW
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    QIntWidget,
    QPlotCanvas,
)
from himena_relion import _job

_LOGGER = logging.getLogger(__name__)


@register_job(_job.Refine3DJobDirectory)
class QRefine3DViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        layout = self._layout
        self._viewer = Q3DViewer()
        self._viewer.setMaximumHeight(480)
        self._fsc_plot = QPlotCanvas(self)
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
        layout.addWidget(self._fsc_plot)

        self._index_start = 1
        self._job_dir: _job.Refine3DJobDirectory | None = None

        self._iter_choice.valueChanged.connect(self._on_iter_changed)
        self._class_choice.valueChanged.connect(self._on_class_changed)

    def on_job_updated(self, job_dir: _job.Refine3DJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_id)

    def initialize(self, job_dir: _job.Refine3DJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        nclasses = job_dir.num_classes()
        if nclasses == 0:
            return
        niters = job_dir.num_iters()
        self._class_choice.setMaximum(nclasses)
        self._iter_choice.setMaximum(max(niters - 1, 0))
        self._iter_choice.setValue(self._iter_choice.maximum())
        self._on_iter_changed(self._iter_choice.value())
        self._viewer.auto_threshold()
        self._viewer.auto_fit()

    def _on_iter_changed(self, value: int):
        self._update_for_value(value, self._class_choice.value())

    def _on_class_changed(self, value: int):
        self._update_for_value(self._iter_choice.value(), value)

    def _update_for_value(self, niter: int, class_id: int):
        res = self._job_dir.get_result(niter)
        map0, map1 = res.halfmaps(class_id - self._index_start)
        if map0 is not None and map1 is not None:
            self._viewer.set_image(map0 + map1)
        else:
            self._viewer.set_image(None)
        df_fsc = res.fsc_dataframe(class_id)
        if df_fsc is not None:
            self._fsc_plot.plot_fsc_refine(df_fsc)
