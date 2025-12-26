from __future__ import annotations
from pathlib import Path
import logging
from qtpy import QtWidgets as QtW
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    register_job,
    spacer_widget,
)
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job(_job_dir.ExtractJobDirectory)
class QExtractJobViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job_dir.ExtractJobDirectory | None = None
        self._viewer = Q2DViewer()
        self._tomo_choice = QtW.QComboBox()
        self._tomo_choice.currentTextChanged.connect(self._on_tomo_changed)
        self._particle_offset = QtW.QSpinBox()
        self._particle_offset.setRange(1, 1)
        self._particle_offset.valueChanged.connect(self._on_spinbox_changed)
        hlayout = QtW.QHBoxLayout()
        hlayout.addWidget(self._tomo_choice)
        hlayout.addWidget(self._particle_offset)
        self._layout.addLayout(hlayout)
        self._dimension_label = QtW.QLabel()
        self._layout.addWidget(self._dimension_label)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(spacer_widget())

    def on_job_updated(self, job_dir: _job_dir.ExtractJobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.name.endswith(
            ("_stack2d.mrcs", "_data.mrc")
        ):
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", self._job_dir.job_id)

    def initialize(self, job_dir: _job_dir.ExtractJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        # update choices, don't include tomogram IDs with no subtomograms
        subtomo_dir = job_dir.path.joinpath("Subtomograms")
        if not subtomo_dir.exists():
            return
        tomo_names = [
            path.name
            for path in subtomo_dir.iterdir()
            if path.is_dir() and (next(path.iterdir(), None) is not None)
        ]
        existing_names = [
            self._tomo_choice.itemText(i) for i in range(self._tomo_choice.count())
        ]
        if set(tomo_names) != set(existing_names):
            self._tomo_choice.clear()
            self._tomo_choice.addItems(tomo_names)

        self._set_tomo_name_and_particle_list(
            self._tomo_choice.currentText(), self._particle_offset.value()
        )
        self._on_spinbox_changed(self._particle_offset.value())
        _type = "2D stacks" if job_dir.is_2d() else "3D Subtomograms"
        self._dimension_label.setText(f"Extraction method: {_type}")

    def _on_tomo_changed(self, value: str):
        if self._job_dir is None:
            return
        self._set_tomo_name_and_particle_list(value, 0)
        self._update_offset_range(value)

    def _update_offset_range(self, value: str):
        max_num = self._job_dir.max_num_subtomograms(value)
        self._particle_offset.setMaximum(max(0, max_num))
        self._viewer.auto_fit()

    def _on_spinbox_changed(self, value: int):
        tomo_name = self._tomo_choice.currentText()
        self._set_tomo_name_and_particle_list(tomo_name, value)

    def _set_tomo_name_and_particle_list(self, tomo_name: str, offset: int):
        for i, (_, img) in enumerate(
            self._job_dir.iter_subtomograms(tomo_name, [offset])
        ):
            if img is None:
                self._viewer.clear()
            else:
                self._viewer.set_array_view(img)
            self._viewer.redraw()
