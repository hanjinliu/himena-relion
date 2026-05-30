from __future__ import annotations
from pathlib import Path

import logging
from qtpy import QtWidgets as QtW, QtCore
from starfile_rs import read_star_block
import mrcfile
import numpy as np
from superqt import QToggleSwitch
from superqt.utils import thread_worker
from himena.widgets import current_instance
from himena_relion._widgets._shared.resizer import QResizer
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    QIntWidget,
    QMicrographListWidget,
    QSymmetryLabel,
    QNumParticlesLabel,
)
from himena_relion import _job_dir
from himena_relion._utils import wait_for_file

_LOGGER = logging.getLogger(__name__)


@register_job("relion.class3d", is_tomo=True)
class QClass3DViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.Class3DJobDirectory):
        from himena_relion._widgets._vispy import MaskMesh

        super().__init__()
        self._list_widget = QMicrographListWidget(
            [
                "Class",
                "Population",
                "Resolution",
                "Rot. Accuracy",
                "Trans. Accuracy",
            ]
        )
        self._list_widget.verticalHeader().setVisible(False)
        self._list_widget.setMinimumWidth(300)
        self._list_widget.setMaximumWidth(400)

        self._viewer = Q3DViewer()
        _arrow_visible_default = False
        self._viewer._canvas.arrow_visual.visible = _arrow_visible_default
        self._arrow_visible = QToggleSwitch("Angle distribution")
        self._arrow_visible.setChecked(_arrow_visible_default)
        self._arrow_visible.toggled.connect(self._on_arrow_visible_toggled)
        self._arrow_visible.setToolTip(
            "Show the particle angle distribution as arrows on the 3D map.\n"
            "The _angdist.bild output file of the selected iteration and class index \n"
            "is used to generate the arrows."
        )
        self._resizer = QResizer(self._viewer)
        self._symmetry_label = QSymmetryLabel()
        self._iter_choice = QIntWidget("Iteration", label_width=60)
        self._iter_choice.setMinimum(0)
        self._continue_from_here_btn = QtW.QPushButton("Continue ...")
        self._continue_from_here_btn.setStyleSheet("padding: 2px; border-radius: 4px;")
        self._continue_from_here_btn.setToolTip(
            "Click to continue 3D classification job from this iteration."
        )
        self._continue_from_here_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._continue_from_here_btn.clicked.connect(self._continue_from_here_clicked)
        self._num_particles_label = QNumParticlesLabel()
        hor1 = QtW.QWidget()
        hor1.setMaximumWidth(400)
        hor1.setFixedHeight(26)
        hor_layout = QtW.QHBoxLayout(hor1)
        hor_layout.setContentsMargins(0, 0, 0, 0)
        hor_layout.addWidget(self._arrow_visible)
        hor_layout.addWidget(self._symmetry_label)
        hor2 = QtW.QWidget()
        hor2.setMaximumWidth(400)
        hor_layout = QtW.QHBoxLayout(hor2)
        hor_layout.setContentsMargins(0, 0, 0, 0)
        hor_layout.addWidget(self._iter_choice)
        hor_layout.addWidget(self._continue_from_here_btn)
        hor_layout.addWidget(self._num_particles_label)
        self._index_start = 1
        self._job_dir = job_dir

        self._layout.setSpacing(0)
        self._layout.addWidget(self._list_widget)
        self._layout.addWidget(hor1)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(self._resizer)
        self._layout.addWidget(hor2)

        self._iter_choice.valueChanged.connect(self._on_iter_changed)
        self._list_widget.current_changed.connect(self._on_class_changed)

        # show mask for iter=0
        self._mesh_layer = MaskMesh(parent=self._viewer._canvas._viewbox.scene)
        self._mesh_layer.visible = False

    def on_job_updated(self, job_dir: _job_dir.Class3DJobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.name.endswith("_model.star"):
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def initialize(self, job_dir: _job_dir.Class3DJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        nclasses = job_dir.num_classes()
        if nclasses == 0:
            return
        self._list_widget.setFixedHeight(min(nclasses * 22 + 18, 110))
        niters = job_dir.num_iters()
        self._iter_choice.setMaximum(max(niters, 0))
        self._iter_choice.setValue(self._iter_choice.maximum())
        self._on_iter_changed(self._iter_choice.value())
        sym_name = self._job_dir.get_job_param("sym_name")
        self._symmetry_label.set_symmetry(sym_name)

    def _on_iter_changed(self, value: int):
        class_id = int(self._list_widget.current_text() or 1)
        self._update_for_value(value, class_id)
        self._update_summary_table(value)

    def _continue_from_here_clicked(self):
        is_no_alignment = self._job_dir.get_job_param("dont_skip_align", "Yes") == "No"
        if self._job_dir.is_tomo():
            if is_no_alignment:
                from himena_relion.relion5_tomo._continues import (
                    Class3DTomoNoAlignmentContinue as C,
                )
            else:
                from himena_relion.relion5_tomo._continues import (
                    Class3DTomoContinue as C,
                )
        else:
            if is_no_alignment:
                from himena_relion.relion5._continues import (
                    Class3DNoAlignmentContinue as C,
                )
            else:
                from himena_relion.relion5._continues import Class3DContinue as C

        niter = self._iter_choice.value()
        optimiser_path = self._job_dir.path / f"run_it{niter:03d}_optimiser.star"
        if not optimiser_path.exists():
            raise FileNotFoundError(
                f"Optimiser STAR file not found for iteration {niter} (should be at "
                f"{optimiser_path})"
            )
        fn_cont = self._job_dir.make_relative_path(optimiser_path).as_posix()
        ui = current_instance()
        C._show_scheduler_widget_for_continue(
            ui, {"fn_cont": fn_cont, "_job_dir": self._job_dir}
        )

    def _on_class_changed(self, value: tuple[str, str, str]):
        class_id = int(value[0])
        self._update_for_value(self._iter_choice.value(), class_id)

    def _update_for_value(self, niter: int, class_id: int):
        self.window_closed_callback()
        self._mesh_layer.visible = niter == 0
        job_dir = self._job_dir
        if (
            niter == 0
            and (optimiser_star := job_dir.path / "run_it000_optimiser.star").exists()
        ):
            try:
                opt_gen = read_star_block(optimiser_star, "optimiser_general")
                mask_path = job_dir.resolve_path(
                    opt_gen.trust_single().get("rlnSolventMaskName", "None")
                )
                if mask_path.exists():
                    with mrcfile.open(mask_path) as mrc:
                        mask = np.asarray(mrc.data, np.float32)
                    self._mesh_layer.set_data(mask, level=0.5, step=2)
            except Exception:
                _LOGGER.warning("Failed to load mask for iteration 0", exc_info=True)
                self._mesh_layer.visible = False

        self._worker = self._read_items(niter, class_id)
        self._start_worker()

    def _update_summary_table(self, niter):
        res = self._job_dir.get_result(niter)
        try:
            gr = res.model_groups()
        except Exception:
            _LOGGER.warning(
                "Failed to read model star for iteration %s", niter, exc_info=True
            )
            return
        nclasses = len(gr.classes.class_distribution)
        choices = []
        for ith in range(nclasses):
            dist = gr.classes.class_distribution[ith]
            reso = _format_float(gr.classes.resolution[ith], "A")
            rot = _format_float(gr.classes.accuracy_rotation[ith], "deg")
            trans = _format_float(gr.classes.accyracy_translation[ith], "A")
            choices.append((str(ith + 1), f"{dist:.2%}", reso, rot, trans))
        self._list_widget.set_choices(choices)

    def _on_arrow_visible_toggled(self, checked: bool):
        self._viewer._canvas.arrow_visual.visible = checked
        self._viewer._canvas.update_canvas()

    @thread_worker
    def _read_items(self, niter, class_id):
        res = self._job_dir.get_result(niter)
        map0, scale = res.class_map(class_id - self._index_start)
        was_empty = not self._viewer.has_image
        yield self._viewer.set_image, map0
        if was_empty:
            yield self._auto_threshold_and_fit, None
        tubes = res.angdist(class_id, scale)
        yield self._viewer._canvas.set_arrows, tubes
        if wait_for_file(res._data_star(), num_retry=100, delay=0.3):
            try:
                part = res.particles()
            except Exception:
                # STAR file may not be ready when the number of particles is large.
                pass
            else:
                num_particles = len(part.particles.block)
                yield self._num_particles_label.set_number_for_class3d, num_particles
        self._worker = None

    def _auto_threshold_and_fit(self, *_):
        self._viewer.auto_threshold()
        self._viewer.auto_fit()


def _format_float(value: float, unit: str) -> str:
    if value >= 998.99:
        return "N/A"
    return f"{value:.2f} {unit}"
