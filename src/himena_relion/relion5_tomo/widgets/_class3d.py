from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore
from himena_relion._widgets import JobWidgetBase, Q3DViewer, register_job
from himena_relion import _job


@register_job(_job.Class3DJobDirectory)
class QClass3DViewer(QtW.QScrollArea, JobWidgetBase):
    def __init__(self):
        super().__init__()
        inner = QtW.QWidget()
        self.setWidget(inner)
        self.setWidgetResizable(True)
        layout = QtW.QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        viewer_row_scroll_area = QtW.QScrollArea()
        viewer_row = QtW.QWidget()
        viewer_row.setMaximumWidth(520)
        layout_viewer = QtW.QHBoxLayout(viewer_row)
        layout_viewer.setContentsMargins(0, 0, 0, 0)
        layout_viewer.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft
        )
        viewer_row_scroll_area.setWidget(viewer_row)
        viewer_row_scroll_area.setWidgetResizable(True)
        self._layout_viewer = layout_viewer
        self._viewers: list[Q3DViewer] = []
        viewer_row.setFixedHeight(240)
        self._iter_choice = QtW.QComboBox()
        layout.addWidget(viewer_row)
        layout.addWidget(self._iter_choice)
        self._index_start = 1
        self._job_dir: _job.Class3DJobDirectory | None = None
        self._iter_choice.currentIndexChanged.connect(self._on_iter_changed)

    def on_job_updated(self, job_dir: _job.Class3DJobDirectory, path: str):
        """Handle changes to the job directory."""
        self._update_for_job_dir(job_dir)

    def initialize(self, job_dir: _job.Class3DJobDirectory):
        """Initialize the viewer with the job directory."""
        nclasses = job_dir.num_classes()
        if nclasses == 0:
            return
        niters = job_dir.num_iters()
        for _ in range(nclasses):
            viewer = Q3DViewer()
            viewer.setFixedSize(QtCore.QSize(200, 200))
            self._viewers.append(viewer)
            self._layout_viewer.addWidget(viewer)
        self._iter_choice.addItems([f"iter {i}" for i in range(0, niters)])
        self._iter_choice.setCurrentIndex(self._iter_choice.count() - 1)
        self._update_for_job_dir(job_dir)

    def _update_for_job_dir(self, job_dir: _job.Class3DJobDirectory, index: int = -1):
        self._job_dir = job_dir
        nclasses = len(self._viewers)
        if index < 0:
            index = self._iter_choice.currentIndex()
        res = job_dir.get_result(index)
        dist = res.value_ratio(nclasses)
        for iclass in range(nclasses):
            map_refined = res.class_map(iclass)
            self._viewers[iclass].set_image(map_refined)
            self._viewers[iclass].set_text_overlay(
                f"Class {iclass + self._index_start} ({dist.get(iclass, 0.0):.1%})"
            )

    def _on_iter_changed(self, index: int):
        """Handle changes to the iteration choice."""
        if not self._viewers:
            return
        job_dir = self._job_dir
        if job_dir is None:
            return
        self._update_for_job_dir(job_dir, index)
