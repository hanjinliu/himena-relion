from __future__ import annotations

from pathlib import Path
import uuid
import mrcfile
import numpy as np
from qtpy import QtWidgets as QtW, QtCore
import logging
from superqt.utils import thread_worker
from himena_relion import _job_dir, _utils
from himena_relion._widgets import (
    QJobScrollArea,
    register_job,
    QMicrographListWidget,
    QImageViewTextEdit,
    QNumParticlesLabel,
)

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
        self._num_particles_label = QNumParticlesLabel()
        self._text_edit = QImageViewTextEdit(font_size=11)
        self._text_edit.setMinimumHeight(350)
        self._slider = QtW.QSlider(QtCore.Qt.Orientation.Horizontal)
        self._slider_display_range = QtW.QLabel("?? - ??")
        self._mic_list = QMicrographListWidget(["Micrograph", "Extracted", "Full Path"])
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
        layout.addWidget(self._num_particles_label)
        layout.addWidget(self._mic_list)
        self._slider.valueChanged.connect(self._slider_value_changed)
        self._plot_session_id = self._text_edit.prep_uuid()
        self._nparticles_cache: dict[str, int] = {}

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".star":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        choices = []
        num_total = 0
        for mrcs_path in self._job_dir.glob_in_subdirs("*.mrcs"):
            fp = self._job_dir.make_relative_path(mrcs_path)
            rel_path = fp.as_posix()
            nparticles = self._nparticles_cache.get(rel_path)
            if nparticles is None or nparticles == 0:
                with mrcfile.open(mrcs_path, header_only=True) as mrc:
                    nparticles = mrc.header.nz
                self._nparticles_cache[rel_path] = nparticles
            choices.append((fp.name, str(nparticles), rel_path))
            num_total += nparticles
        self._mic_list.set_choices(choices)
        self._num_particles_label.set_number(num_total)

    def _mic_changed(self, row: tuple[str, str, str]):
        """Handle changes to selected micrograph."""
        rln_dir = self._job_dir.relion_project_dir
        self._current_extract_path = rln_dir / row[2]
        nz = int(row[1])
        self._current_num_extracts = nz
        current_pos = self._slider.value()
        self._slider.setRange(0, nz // self._num_page)
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
        self._start_worker()

    @thread_worker
    def plot_extracts(self, start_index: int, session: uuid.UUID):
        end_index = min(start_index + self._num_page, self._current_num_extracts + 1)
        with mrcfile.mmap(self._current_extract_path) as mrc:
            mrc_data = mrc.data
            for ith in range(start_index + 1, end_index + 1):
                if mrc_data.shape[0] < ith:
                    break
                img_data = np.asarray(mrc_data[ith - 1], dtype=np.float32)
                img_data = _utils.lowpass_filter(img_data, 0.2)
                img_str = self._text_edit.image_to_base64(img_data, f"{ith}")
                yield self._on_string_ready, (img_str, session)

    def _on_string_ready(self, value: tuple[str, uuid.UUID]):
        if self._worker is None:
            return
        img_str, my_uuid = value
        if my_uuid != self._plot_session_id:
            return
        self._text_edit.insert_base64_image(img_str)
