from __future__ import annotations
from pathlib import Path

from qtpy import QtWidgets as QtW, QtCore, QtGui
from himena_relion._widgets import JobWidgetBase, Q3DViewer, register_job, QIntWidget
from himena_relion import _job
from himena_relion.relion5_tomo.widgets._shared import standard_layout


@register_job(_job.Class3DJobDirectory)
class QClass3DViewer(QtW.QScrollArea, JobWidgetBase):
    def __init__(self):
        super().__init__()
        layout = standard_layout(self)
        self._viewer = Q3DViewer()
        self._viewer.setFixedSize(300, 300)
        self._percentage_label = QtW.QLabel("0%")
        self._percentage_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        font = self._percentage_label.font()
        font.setPointSize(8)
        self._percentage_label.setFont(font)
        self._percentage_label.setFixedSize(300, QtGui.QFontMetrics(font).height() + 2)
        self._class_choice = QIntWidget("Class", label_width=50)
        self._iter_choice = QIntWidget("Iteration", label_width=60)
        self._class_choice.setMinimum(1)
        self._iter_choice.setMinimum(0)
        layout.addWidget(self._viewer)
        layout.addWidget(self._percentage_label)
        hor_layout = QtW.QHBoxLayout()
        hor_layout.addWidget(self._iter_choice)
        hor_layout.addWidget(self._class_choice)
        hor_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(hor_layout)
        self._index_start = 1
        self._job_dir: _job.Class3DJobDirectory | None = None

        self._iter_choice.valueChanged.connect(self._on_iter_changed)
        self._class_choice.valueChanged.connect(self._on_class_changed)

    def on_job_updated(self, job_dir: _job.Class3DJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix not in [".out", ".err", ".star"]:
            self.initialize(job_dir)

    def initialize(self, job_dir: _job.Class3DJobDirectory):
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
        map0 = res.class_map(class_id - self._index_start)
        self._viewer.set_image(map0)
        ratio = res.value_ratio()[class_id]
        self._percentage_label.setText(f"{ratio * 100:.2f}%")
