from __future__ import annotations

from pathlib import Path
import uuid
import mrcfile
import numpy as np
from qtpy import QtWidgets as QtW, QtCore
import logging
from superqt.utils import GeneratorWorker, thread_worker
from himena_relion import _job_dir, _utils
from ._shared import QMicrographListWidget, QImageViewTextEdit
from himena_relion._widgets import QJobScrollArea, register_job

_LOGGER = logging.getLogger(__name__)


@register_job("relion.extract")
@register_job("relion.extract.reextract")
class QExtractViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._current_extract_path = None
        self._current_num_extracts = 0
        self._num_page = 50
        self._worker: GeneratorWorker | None = None
        self._text_edit = QImageViewTextEdit(font_size=11)
        self._slider = QtW.QSlider(QtCore.Qt.Orientation.Horizontal)
        self._slider_display_range = QtW.QLabel("?? - ??")
        self._mic_list = QMicrographListWidget(["Micrograph"])
        self._mic_list.setFixedHeight(130)
        self._mic_list.current_changed.connect(self._mic_changed)
        layout.addWidget(QtW.QLabel("<b>Extracted Micrographs</b>"))
        hlayout = QtW.QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(QtW.QLabel("Display Range:"))
        hlayout.addWidget(self._slider)
        hlayout.addWidget(self._slider_display_range)

        layout.addLayout(hlayout)
        layout.addWidget(self._text_edit)
        layout.addWidget(self._mic_list)
        self._slider.valueChanged.connect(self._slider_value_changed)
        self._plot_session_id = self._text_edit.prep_uuid()

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".star":
            self._process_update()
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        self._process_update()

    def _process_update(self):
        choices = []
        movies_dir = self._job_dir.path / "Movies"
        for mrcs_path in movies_dir.glob("*.mrcs"):
            choices.append((self._job_dir.make_relative_path(mrcs_path).as_posix(),))
        self._mic_list.set_choices(choices)

    def _mic_changed(self, row: tuple[str]):
        """Handle changes to selected micrograph."""
        rln_dir = self._job_dir.relion_project_dir
        self._current_extract_path = rln_dir / row[0]
        with mrcfile.open(self._current_extract_path, header_only=True) as mrc:
            nz = mrc.header.nz
        self._current_num_extracts = nz
        current_pos = self._slider.value()
        self._slider.setRange(1, nz // self._num_page)
        current_pos = min(current_pos, self._slider.maximum())
        self._slider_value_changed(current_pos, udpate_slider=True)

    def _slider_value_changed(self, value: int, *, udpate_slider: bool = False):
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
        with mrcfile.mmap(self._current_extract_path) as mrc:
            end_index = min(
                start_index + self._num_page, self._current_num_extracts + 1
            )
            for ith in range(start_index, end_index):
                img_data = np.asarray(mrc.data[ith - 1], dtype=np.float32)
                img_data = _utils.lowpass_filter(img_data, 0.2)
                img_str = self._text_edit.image_to_base64(img_data, f"{ith}")
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
