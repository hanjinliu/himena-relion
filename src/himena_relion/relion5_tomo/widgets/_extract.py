from __future__ import annotations
from pathlib import Path
import logging
import uuid
import numpy as np
import mrcfile
from qtpy import QtWidgets as QtW, QtCore
from superqt.utils import GeneratorWorker, thread_worker
from himena_relion._widgets import QJobScrollArea, register_job
from himena_relion import _job_dir, _utils
from himena_relion.relion5.widgets._shared import (
    QImageViewTextEdit,
    QMicrographListWidget,
)

_LOGGER = logging.getLogger(__name__)


@register_job("relion.pseudosubtomo", is_tomo=True)
class QExtractJobViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.ExtractJobDirectory):
        super().__init__()
        self._job_dir = job_dir

        self._num_page = 50
        self._current_num_extracts = 0
        self._subtomo_pattern = "{ith}_data.mrc"
        self._worker: GeneratorWorker | None = None
        self._tomo_list = QMicrographListWidget(["Tomogram", "Subtomogram Path"])
        self._tomo_list.setFixedHeight(130)
        self._tomo_list.current_changed.connect(self._on_tomo_changed)
        self._text_edit = QImageViewTextEdit(font_size=11)
        self._slider = QtW.QSlider(QtCore.Qt.Orientation.Horizontal)
        self._slider_display_range = QtW.QLabel("?? - ??")

        self._subtomogram_label = QtW.QLabel("")
        self._layout.addWidget(self._subtomogram_label)
        hlayout = QtW.QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(QtW.QLabel("Display Range:"))
        hlayout.addWidget(self._slider)
        hlayout.addWidget(self._slider_display_range)

        self._layout.addLayout(hlayout)
        self._layout.addWidget(self._text_edit)
        self._layout.addWidget(self._tomo_list)
        self._slider.valueChanged.connect(self._slider_value_changed)
        self._plot_session_id = self._text_edit.prep_uuid()

    def on_job_updated(self, job_dir: _job_dir.ExtractJobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.name.endswith(
            ("_stack2d.mrcs", "_data.mrc")
        ):
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def initialize(self, job_dir: _job_dir.ExtractJobDirectory):
        """Initialize the viewer with the job directory."""
        # update choices, don't include tomogram IDs with no subtomograms
        self._process_update()

    def _process_update(self):
        subtomo_dir = self._job_dir.path.joinpath("Subtomograms")
        if not subtomo_dir.exists():
            return
        tomo_names = [
            (
                path.name,
                self._job_dir.make_relative_path(subtomo_dir / path.name).as_posix(),
            )
            for path in subtomo_dir.iterdir()
            if path.is_dir() and (next(path.iterdir(), None) is not None)
        ]
        tomo_names.sort(key=lambda x: x[0])
        self._tomo_list.set_choices(tomo_names)
        if self._job_dir.is_2d():
            self._subtomogram_label.setText("<b>Extracted 2D stacks (zero tilt)</b>")
            self._subtomo_pattern = "{ith}_stack2d.mrcs"
        else:
            self._subtomogram_label.setText(
                "<b>Extracted subtomograms (max projection)</b>"
            )
            self._subtomo_pattern = "{ith}_data.mrc"

    def _on_tomo_changed(self, value: tuple[str, str]):
        tomo_name = value[0]
        max_num = self._job_dir.max_num_subtomograms(tomo_name)
        self._current_num_extracts = max_num
        current_pos = self._slider.value()
        self._slider.setRange(0, max_num // self._num_page)
        current_pos = min(current_pos, self._slider.maximum())
        self._slider_value_changed(current_pos, udpate_slider=True)

    def _slider_value_changed(self, value: int, *, udpate_slider: bool = False):
        # value: 0-indexed
        self.window_closed_callback()
        if udpate_slider:
            self._slider.setValue(value)
        self._text_edit.clear()
        self._plot_session_id = self._text_edit.prep_uuid()
        start = value * self._num_page
        # Adjust for 1-based indexing
        self._slider_display_range.setText(
            f"{start + 1} - {min(start + self._num_page, self._current_num_extracts)}"
        )
        self._worker = self.plot_extracts(start, self._plot_session_id)
        self._worker.yielded.connect(self._on_yielded)
        self._worker.start()

    @thread_worker
    def plot_extracts(self, start_index: int, session: uuid.UUID):
        subtomo_dir = self._tomo_list.current_text(1)
        end_index = min(start_index + self._num_page, self._current_num_extracts + 1)
        subtomo_dir = self._job_dir.resolve_path(subtomo_dir)
        for ith in range(start_index + 1, end_index + 1):
            mrc_path = subtomo_dir / self._subtomo_pattern.format(ith=ith)
            if not mrc_path.exists():
                img_str = self._text_edit.image_to_base64(
                    np.zeros((2, 2), dtype=np.float32), f"{ith}"
                )
                yield img_str, session
                continue
            with mrcfile.mmap(mrc_path) as mrc:
                img_data = np.asarray(mrc.data, dtype=np.float32)
                if self._subtomo_pattern.endswith("_stack2d.mrcs"):
                    img_2d = img_data[img_data.shape[0] // 2, :, :]
                else:
                    img_2d = np.max(img_data, axis=0)
                img_2d = _utils.lowpass_filter(img_2d, 0.2)
                img_str = self._text_edit.image_to_base64(img_2d, f"{ith}")
                yield img_str, session

    def _on_yielded(self, value: tuple[str, uuid.UUID]):
        if self._worker is None:
            return
        img_str, my_uuid = value
        if my_uuid != self._plot_session_id:
            return
        self._text_edit.insert_base64_image(img_str)

    def window_closed_callback(self):
        if self._worker:
            worker = self._worker
            self._worker = None
            worker.quit()

    def closeEvent(self, a0):
        self.window_closed_callback()
        return super().closeEvent(a0)
