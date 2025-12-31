from __future__ import annotations
from pathlib import Path

import logging
from qtpy import QtWidgets as QtW
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    QIntWidget,
    spacer_widget,
    QMicrographListWidget,
)
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job("relion.class3d", is_tomo=True)
class QClass3DViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.Class3DJobDirectory):
        super().__init__()
        self._list_widget = QMicrographListWidget(["Class", "Population", "Resolution"])
        self._list_widget.verticalHeader().setVisible(False)
        self._list_widget.setFixedWidth(200)
        self._viewer = Q3DViewer()
        self._iter_choice = QIntWidget("Iteration", label_width=60)
        self._iter_choice.setMinimum(0)
        hor_layout0 = QtW.QHBoxLayout()
        hor_layout0.addWidget(self._viewer)
        hor_layout0.addWidget(self._list_widget)
        self._layout.addLayout(hor_layout0)
        hor_layout1 = QtW.QHBoxLayout()
        hor_layout1.addWidget(self._iter_choice)
        hor_layout1.setContentsMargins(0, 0, 0, 0)
        self._layout.addLayout(hor_layout1)
        self._index_start = 1
        self._job_dir = job_dir

        self._iter_choice.valueChanged.connect(self._on_iter_changed)
        self._list_widget.current_changed.connect(self._on_class_changed)
        self._layout.addWidget(spacer_widget())

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

    def _on_iter_changed(self, value: int):
        class_id = int(self._list_widget.current_text() or 1)
        self._update_for_value(value, class_id)
        self._update_summary_table(value)

    def _on_class_changed(self, value: tuple[str, str, str]):
        class_id = int(value[0])
        self._update_for_value(self._iter_choice.value(), class_id)

    def _update_for_value(self, niter: int, class_id: int):
        res = self._job_dir.get_result(niter)
        map0 = res.class_map(class_id - self._index_start)
        self._viewer.set_image(map0)

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
            reso = gr.classes.resolution[ith]
            choices.append((str(ith + 1), f"{dist:.2%}", f"{reso:.2f} A"))
        self._list_widget.set_choices(choices)
