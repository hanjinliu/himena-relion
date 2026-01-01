from __future__ import annotations
from pathlib import Path
import logging
from typing import Any, Callable
import numpy as np
import pandas as pd
from qtpy import QtWidgets as QtW, QtCore
from superqt.utils import thread_worker
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    QIntWidget,
    QPlotCanvas,
    spacer_widget,
    QNumParticlesLabel,
)
from himena_relion import _job_dir
from himena_relion.schemas import ParticleMetaModel

_LOGGER = logging.getLogger(__name__)


@register_job("relion.refine3d")
@register_job("relion.refine3d.tomo", is_tomo=True)
class QRefine3DViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        layout = self._layout
        self._viewer = Q3DViewer()
        max_width = 400
        self._viewer.setMaximumWidth(max_width)
        self._fsc_plot = QPlotCanvas(self)
        self._ang_dist_plot = QPlotCanvas(self)
        self._iter_choice = QIntWidget("Iteration", label_width=60)
        self._iter_choice.setMinimum(0)
        self._num_particles_label = QNumParticlesLabel()
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
        layout.addWidget(QtW.QLabel("<b>Angle Distribution</b>"))
        layout.addWidget(self._ang_dist_plot)
        layout.addWidget(spacer_widget())
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

        map0, map1 = res.halfmaps(class_id - self._index_start)
        if map0 is not None and map1 is not None:
            map_out = map0 + map1
        else:
            map_out = None
        yield self._set_map, map_out
        df_fsc, df_groups = res.model_dataframe(class_id)
        yield self._set_fsc, df_fsc
        if df_groups is not None:
            num_particles = df_groups["rlnGroupNrParticles"].sum()
        else:
            num_particles = 0
        yield self._set_num_particles, num_particles

        path_data = self._job_dir.path / f"run_it{niter:0>3}_data.star"
        if not path_data.exists():
            yield self._set_ang_dist, None
            return
        model = ParticleMetaModel.validate_file(path_data)
        part = model.particles
        if part.angle_rot is not None and part.angle_tilt is not None:
            rot = part.angle_rot.fillna(0.0)
            tilt = part.angle_tilt.fillna(0.0)
            heatmap, _, _ = np.histogram2d(
                rot,
                tilt,
                bins=[36, 18],
                range=[[-180, 180], [0, 180]],
            )
            yield self._set_ang_dist, heatmap.T
        else:
            yield self._set_ang_dist, None
        self._worker = None

    def _on_yielded(self, yielded: tuple[Callable, Any]):
        fn, args = yielded
        fn(args)

    def _set_map(self, map_data: np.ndarray | None):
        self._viewer.set_image(map_data)

    def _set_fsc(self, df_fsc: pd.DataFrame | None):
        if df_fsc is not None:
            self._fsc_plot.plot_fsc_refine(df_fsc)
        else:
            self._fsc_plot.clear()

    def _set_num_particles(self, num_particles: int):
        self._num_particles_label.set_number(num_particles)

    def _set_ang_dist(self, heatmap: np.ndarray | None):
        if heatmap is not None:
            axes = self._ang_dist_plot.figure.axes[0]
            axes.imshow(heatmap, cmap="viridis")
            axes.set_xlabel("Rot (deg)")
            axes.set_ylabel("Tilt (deg)")
            axes.set_xticks(
                [0, 9, 18, 27, 36], labels=["-180", "-90", "0", "90", "180"]
            )
            axes.set_yticks([0, 9, 18], labels=["0", "90", "180"])
            self._ang_dist_plot.tight_layout()
            self._ang_dist_plot._canvas.draw()
        else:
            self._ang_dist_plot.clear()

    def widget_added_callback(self):
        self._fsc_plot.widget_added_callback()
