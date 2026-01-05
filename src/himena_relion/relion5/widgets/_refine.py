from __future__ import annotations
from pathlib import Path
import logging
from typing import Any, Callable
import pandas as pd
from qtpy import QtWidgets as QtW, QtCore
from superqt import QToggleSwitch
from superqt.utils import thread_worker
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    QIntWidget,
    QPlotCanvas,
    QNumParticlesLabel,
    QSymmetryLabel,
)
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job("relion.refine3d")
@register_job("relion.refine3d.tomo", is_tomo=True)
class QRefine3DViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        layout = self._layout
        self._viewer = Q3DViewer()
        _arrow_visible_default = False
        self._arrow_visible = QToggleSwitch("Show angle distribution")
        self._arrow_visible.setChecked(_arrow_visible_default)
        self._arrow_visible.toggled.connect(self._on_arrow_visible_toggled)
        self._arrow_visible.setToolTip(
            "Show the particle angle distribution as arrows on the 3D map.\n"
            "The _angdist.bild output file of the selected iteration is used to\n"
            "generate the arrows."
        )
        self._symmetry_label = QSymmetryLabel()
        self._viewer._canvas.arrow_visual.visible = _arrow_visible_default
        max_width = 400
        self._viewer.setMaximumWidth(max_width)
        self._fsc_plot = QPlotCanvas(self)
        self._iter_choice = QIntWidget("Iteration", label_width=60)
        self._iter_choice.setMinimum(0)
        self._num_particles_label = QNumParticlesLabel()
        layout.addWidget(QtW.QLabel("<b>Refined Map</b>"))
        hor_layout = QtW.QHBoxLayout()
        hor_layout.setContentsMargins(0, 0, 0, 0)
        hor_layout.addWidget(self._arrow_visible)
        hor_layout.addWidget(self._symmetry_label)
        layout.addLayout(hor_layout)
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
        layout.addWidget(QtW.QLabel("<b>Fourier Shell Correlation</b>"))
        layout.addWidget(self._fsc_plot)
        self._index_start = 1
        self._job_dir = _job_dir.Refine3DJobDirectory(job_dir.path)

        self._iter_choice.valueChanged.connect(self._on_iter_changed)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        niters = self._job_dir.num_iters()
        self._iter_choice.setMaximum(max(niters - 1, 0))
        self._iter_choice.setValue(self._iter_choice.maximum())
        self._on_iter_changed(self._iter_choice.value())
        sym_name = self._job_dir.get_job_param("sym_name")
        self._symmetry_label.set_symmetry(sym_name)

    def _on_iter_changed(self, value: int):
        self._update_for_value(value)

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

        map0, map1, scale = res.halfmaps(class_id - self._index_start)
        if map0 is not None and map1 is not None:
            map_out = map0 + map1
        else:
            map_out = None
        yield self._viewer.set_image, map_out
        df_fsc, groups = res.model_dataframe(class_id)
        yield self._set_fsc, df_fsc
        if groups is not None:
            yield self._num_particles_label.set_number, groups.num_particles.sum()

        if scale is not None:
            tubes = res.angdist(class_id, scale)
            yield self._viewer._canvas.set_arrows, tubes
        self._worker = None

    def _on_yielded(self, yielded: tuple[Callable, Any]):
        fn, args = yielded
        fn(args)

    def _on_arrow_visible_toggled(self, checked: bool):
        self._viewer._canvas.arrow_visual.visible = checked
        self._viewer._canvas.update_canvas()

    def _set_fsc(self, df_fsc: pd.DataFrame | None):
        if df_fsc is not None:
            self._fsc_plot.plot_fsc_refine(df_fsc)
        else:
            self._fsc_plot.clear()

    def widget_added_callback(self):
        self._fsc_plot.widget_added_callback()
