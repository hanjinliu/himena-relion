from __future__ import annotations
from pathlib import Path
import logging
import polars as pl
from qtpy import QtWidgets as QtW, QtCore
from superqt import QToggleSwitch
from starfile_rs import read_star
import mrcfile
from superqt.utils import thread_worker
from himena_relion.schemas import ModelGroups
from himena_relion._utils import wait_for_file
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

        self._iter_choice.valueChanged.connect(self._update_for_value)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.name.endswith("_data.star"):
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        niters = self._job_dir.num_iters()
        self._iter_choice.setMaximum(max(niters - 1, 0))
        self._iter_choice.setValue(self._iter_choice.maximum())
        self._update_for_value(self._iter_choice.value())
        sym_name = self._job_dir.get_job_param("sym_name")
        self._symmetry_label.set_symmetry(sym_name)

    def _update_for_value(self, niter: int):
        self.window_closed_callback()
        self._worker = self._read_items(niter)
        self._start_worker()

    @thread_worker
    def _read_items(self, niter):
        res = self._job_dir.get_result(niter)

        mrc1_path = self._job_dir.path / f"run{res.it_str}_half1_class001.mrc"
        mrc2_path = self._job_dir.path / f"run{res.it_str}_half2_class001.mrc"
        scale = None
        if wait_for_file(mrc1_path) and wait_for_file(mrc2_path):
            with mrcfile.open(mrc1_path, mode="r") as mrc1:
                img1 = mrc1.data
                scale = mrc1.voxel_size.x
            with mrcfile.open(mrc2_path, mode="r") as mrc2:
                img2 = mrc2.data
                scale = mrc2.voxel_size.x
            map_out = (img1 + img2) / 2
            yield self._viewer.set_image, map_out
        model_star = self._job_dir.path / f"run{res.it_str}_half1_model.star"
        if wait_for_file(model_star):
            star = read_star(model_star)
            df_fsc = star["model_class_1"].to_polars()
            groups = ModelGroups.validate_block(star["model_groups"])
            reso = (
                star["model_general"].trust_single().to_dict()["rlnCurrentResolution"]
            )
            yield self._set_fsc, (df_fsc, reso)
            # NOTE: multiply by 2 to account for half-sets
            yield self._num_particles_label.set_number, groups.num_particles.sum() * 2
        else:
            yield self._set_fsc, None
            yield self._num_particles_label.set_number, -1
        bild_path = self._job_dir.path / f"run{res.it_str}_half1_class001_angdist.bild"
        if scale is not None and wait_for_file(bild_path):
            tubes = res.angdist(1, scale)
            yield self._viewer._canvas.set_arrows, tubes
        self._worker = None

    def _on_arrow_visible_toggled(self, checked: bool):
        self._viewer._canvas.arrow_visual.visible = checked
        self._viewer._canvas.update_canvas()

    def _set_fsc(self, val: tuple[pl.DataFrame, float] | None):
        if val is not None:
            self._fsc_plot.plot_fsc_refine(*val)
        else:
            self._fsc_plot.clear()

    def widget_added_callback(self):
        self._fsc_plot.widget_added_callback()
