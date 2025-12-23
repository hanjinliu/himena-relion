from __future__ import annotations
from pathlib import Path
import logging
import numpy as np
import pandas as pd
from qtpy import QtWidgets as QtW, QtCore
from superqt.utils import thread_worker, FunctionWorker
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    QIntWidget,
    QPlotCanvas,
    spacer_widget,
)
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job(_job_dir.Refine3DJobDirectory)
class QRefine3DViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        layout = self._layout
        self._viewer = Q3DViewer()
        max_width = 400
        self._viewer.setMaximumSize(max_width, max_width)
        self._fsc_plot = QPlotCanvas(self)
        self._iter_choice = QIntWidget("Iteration", label_width=60)
        self._iter_choice.setMinimum(0)
        self._num_particles_label = QtW.QLabel("--- particles")
        layout.addWidget(self._viewer)
        _hor = QtW.QWidget()
        _hor.setMaximumWidth(max_width)
        hor_layout = QtW.QHBoxLayout(_hor)
        hor_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        hor_layout.setContentsMargins(0, 0, 0, 0)
        hor_layout.setSpacing(14)
        hor_layout.addWidget(self._iter_choice)
        hor_layout.addWidget(self._num_particles_label)
        layout.addWidget(_hor)
        layout.addWidget(self._fsc_plot)
        layout.addWidget(spacer_widget())
        self._index_start = 1
        self._job_dir: _job_dir.Refine3DJobDirectory | None = None
        self._worker: FunctionWorker | None = None

        self._iter_choice.valueChanged.connect(self._on_iter_changed)

    def on_job_updated(self, job_dir: _job_dir.Refine3DJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_id)

    def initialize(self, job_dir: _job_dir.Refine3DJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        niters = job_dir.num_iters()
        self._iter_choice.setMaximum(max(niters - 1, 0))
        self._iter_choice.setValue(self._iter_choice.maximum())
        self._on_iter_changed(self._iter_choice.value())

    def _on_iter_changed(self, value: int):
        self._update_for_value(value)

    def _update_for_value(self, niter: int, class_id: int = 1):
        if self._worker is not None and self._worker.is_running:
            self._worker.quit()
        self._worker = None
        self._worker = self._read_items(niter, class_id)
        self._worker.returned.connect(self._on_items_read)
        self._worker.start()

    @thread_worker
    def _read_items(self, niter, class_id: int = 1):
        res = self._job_dir.get_result(niter)

        map0, map1 = res.halfmaps(class_id - self._index_start)
        if map0 is not None and map1 is not None:
            map_out = map0 + map1
        else:
            map_out = None
        df_fsc, df_groups = res.model_dataframe(class_id)
        if df_groups is not None:
            num_particles = df_groups["rlnGroupNrParticles"].sum()
        else:
            num_particles = 0
        return map_out, df_fsc, num_particles

    def _on_items_read(self, items: tuple[np.ndarray | None, pd.DataFrame | None, int]):
        map_out, df_fsc, num_particles = items
        had_image = self._viewer.has_image
        self._viewer.set_image(map_out)
        if df_fsc is not None:
            self._fsc_plot.plot_fsc_refine(df_fsc)
        else:
            self._fsc_plot.clear()
        self._num_particles_label.setText(f"<b>{num_particles}</b> particles")
        self._worker = None
        if not had_image:
            self._viewer.auto_threshold(update_now=False)
            self._viewer.auto_fit()

    def widget_added_callback(self):
        self._fsc_plot.widget_added_callback()
