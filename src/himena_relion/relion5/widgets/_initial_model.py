from __future__ import annotations

import logging
from pathlib import Path
from qtpy import QtWidgets as QtW, QtCore
from superqt.utils import thread_worker
from himena.widgets import current_instance
from himena_relion._widgets._shared.resizer import QResizer
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    QMicrographListWidget,
    QIntChoiceWidget,
    QNumParticlesLabel,
    QSymmetryLabel,
)
from himena_relion import _job_dir
from himena_relion.schemas import ModelStarModel

_LOGGER = logging.getLogger(__name__)


@register_job("relion.initialmodel")
@register_job("relion.initialmodel.tomo", is_tomo=True)
class QInitialModelViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.InitialModel3DJobDirectory):
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
        self._resizer = QResizer(self._viewer)

        self._iter_choice = QIntChoiceWidget("Iteration", label_width=60)
        self._iter_choice.setMinimum(0)
        self._continue_from_here_btn = QtW.QPushButton("Continue ...")
        self._continue_from_here_btn.setStyleSheet("padding: 2px; border-radius: 4px;")
        self._continue_from_here_btn.setToolTip(
            "Click to continue initial model job from this iteration."
        )
        self._continue_from_here_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._continue_from_here_btn.clicked.connect(self._continue_from_here_clicked)
        self._num_particles_label = QNumParticlesLabel()
        self._symmetry_label = QSymmetryLabel()
        header = QtW.QWidget()
        header_layout = QtW.QHBoxLayout(header)
        header_layout.setContentsMargins(1, 0, 1, 0)
        header_layout.addWidget(QtW.QLabel("<b>&#9679; Initial Model Map</b>"))
        header_layout.addWidget(self._symmetry_label)
        header.setMaximumWidth(400)

        self._layout.setSpacing(0)
        self._layout.addWidget(self._list_widget)
        self._layout.setSpacing(2)
        self._layout.addWidget(header)
        self._layout.setSpacing(2)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(self._resizer)
        _container2 = QtW.QWidget()
        _container2.setMaximumWidth(400)
        hlayout2 = QtW.QHBoxLayout(_container2)
        hlayout2.addWidget(self._iter_choice)
        hlayout2.addWidget(self._continue_from_here_btn)
        hlayout2.addWidget(self._num_particles_label)
        hlayout2.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(_container2)
        self._iter_choice.current_changed.connect(self._on_iter_changed)
        self._list_widget.current_changed.connect(self._on_class_changed)
        self._index_start = 1
        self._iter_current_value = 0
        self._job_dir = _job_dir.InitialModel3DJobDirectory(job_dir.path)

    def on_job_updated(self, job_dir: _job_dir.InitialModel3DJobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.name.endswith("_model.star"):
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def initialize(self, job_dir: _job_dir.InitialModel3DJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        nclasses = job_dir.num_classes()
        if nclasses == 0:
            return
        self._list_widget.setFixedHeight(min(nclasses * 22 + 18, 110))
        niter_list = self._job_dir.niter_list()
        _LOGGER.info("Job with %s classes", nclasses)
        self._iter_choice.set_choices(niter_list)
        self._iter_choice.setValue(self._iter_choice.maximum())
        self._on_iter_changed(self._iter_choice.value())
        self._viewer.auto_threshold()
        self._viewer.auto_fit()
        sym_name = self._job_dir.get_job_param("sym_name")
        self._symmetry_label.set_symmetry(sym_name)

    def _on_iter_changed(self, value: int):
        class_id = int(self._list_widget.current_text() or 1)
        self._update_for_value(value, class_id)
        self._update_summary_table(value)

    def _on_class_changed(self, value: tuple[str, str, str]):
        class_id = int(value[0])
        self._update_for_value(self._iter_choice.value(), class_id)

    def _continue_from_here_clicked(self):
        if self._job_dir.is_tomo():
            from himena_relion.relion5_tomo._continues import (
                InitialModelTomoContinue as C,
            )
        else:
            from himena_relion.relion5._continues import InitialModelContinue as C

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

    def _update_for_value(self, niter: int, class_id: int = 1):
        if self._worker is not None and self._worker.is_running:
            self._worker.quit()
        self._worker = None
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

    @thread_worker
    def _read_items(self, niter, class_id: int = 1):
        res = self._job_dir.get_result(niter)

        res = self._job_dir.get_result(niter)
        map0, _ = res.class_map(class_id - self._index_start)
        yield self._viewer.set_image, map0
        if self._num_particles_label.num_known():
            return
        starpath = self._job_dir.path / f"run_it{niter:0>3}_model.star"
        if not starpath.exists():
            yield self._num_particles_label.set_number, -1
            return
        try:
            model = ModelStarModel.validate_file(starpath)
            num_particles = model.groups.num_particles.sum()
        except Exception as e:
            num_particles = -1
            raise e
        yield self._num_particles_label.set_number, num_particles


def _format_float(value: float, unit: str) -> str:
    if value >= 998.99:
        return "N/A"
    return f"{value:.2f} {unit}"
