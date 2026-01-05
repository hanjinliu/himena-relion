from __future__ import annotations
from pathlib import Path

import logging
from qtpy import QtWidgets as QtW
from superqt import QToggleSwitch
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    QIntWidget,
    QMicrographListWidget,
    QSymmetryLabel,
)
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job("relion.class3d", is_tomo=True)
class QClass3DViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.Class3DJobDirectory):
        super().__init__()
        self._list_widget = QMicrographListWidget(
            [
                "Class",
                "Population",
                "Resolution",
                "Rotation Accuracy",
                "Translation Accuracy",
            ]
        )
        self._list_widget.verticalHeader().setVisible(False)
        self._viewer = Q3DViewer()
        _arrow_visible_default = False
        self._viewer._canvas.arrow_visual.visible = _arrow_visible_default
        self._arrow_visible = QToggleSwitch("Show angle distribution")
        self._arrow_visible.setChecked(_arrow_visible_default)
        self._arrow_visible.toggled.connect(self._on_arrow_visible_toggled)
        self._arrow_visible.setToolTip(
            "Show the particle angle distribution as arrows on the 3D map.\n"
            "The _angdist.bild output file of the selected iteration and class index \n"
            "is used to generate the arrows."
        )
        self._symmetry_label = QSymmetryLabel()
        self._list_widget.setMinimumWidth(300)
        self._list_widget.setMaximumWidth(400)
        self._iter_choice = QIntWidget("Iteration", label_width=60)
        self._iter_choice.setMinimum(0)
        self._layout.addWidget(self._list_widget)
        hor = QtW.QWidget()
        hor.setMaximumWidth(400)
        hor_layout = QtW.QHBoxLayout(hor)
        hor_layout.setContentsMargins(0, 0, 0, 0)
        hor_layout.addWidget(self._arrow_visible)
        hor_layout.addWidget(self._symmetry_label)
        self._layout.addWidget(hor)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(self._iter_choice)
        self._index_start = 1
        self._job_dir = job_dir

        self._iter_choice.valueChanged.connect(self._on_iter_changed)
        self._list_widget.current_changed.connect(self._on_class_changed)

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
        niters = job_dir.num_iters()
        self._iter_choice.setMaximum(max(niters - 1, 0))
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

    def _update_for_value(self, niter: int, class_id: int):
        res = self._job_dir.get_result(niter)
        map0, scale = res.class_map(class_id - self._index_start)
        self._viewer.set_image(map0)

        tubes = res.angdist(class_id, scale)
        self._viewer._canvas.set_arrows(tubes)

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
        self._viewer._canvas.arrow_visual.update()


def _format_float(value: float, unit: str) -> str:
    if value >= 998.99:
        return "N/A"
    return f"{value:.2f} {unit}"
