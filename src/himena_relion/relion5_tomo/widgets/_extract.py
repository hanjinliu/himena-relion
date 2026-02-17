from __future__ import annotations

import os
from pathlib import Path
import logging
import time
import uuid
import numpy as np
import mrcfile
from qtpy import QtWidgets as QtW, QtCore
from superqt.utils import thread_worker
from himena_relion._widgets import (
    QJobScrollArea,
    register_job,
    QImageViewTextEdit,
    QMicrographListWidget,
)
from himena_relion import _job_dir


_LOGGER = logging.getLogger(__name__)


@register_job("relion.pseudosubtomo", is_tomo=True)
class QExtractJobViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir

        self._last_force_reloaded = -1.0
        self._num_page = 50
        self._last_updated_dir: str = ""
        self._tomo_list = QMicrographListWidget(["Tomogram", "Subtomogram Path"])
        self._tomo_list.setFixedHeight(130)
        self._tomo_list.current_changed.connect(self._on_tomo_changed)
        self._text_edit = QImageViewTextEdit(font_size=11)
        self._text_edit.setMinimumHeight(350)
        self._slider = QtW.QSlider(QtCore.Qt.Orientation.Horizontal)
        self._slider_display_range = QtW.QLabel("?? - ??")

        self._subtomo_label = QtW.QLabel("")
        self._subtomo_paths: list[str] = []
        self._layout.addWidget(self._subtomo_label)
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

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        is_subtomo_update = fp.name.endswith(("_stack2d.mrcs", "_data.mrc"))
        if fp.name.startswith("RELION_JOB_") or is_subtomo_update:
            self.initialize(job_dir)
            if is_subtomo_update:
                self._last_updated_dir = fp.parent.name
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        subtomo_dir = self._job_dir.path.joinpath("Subtomograms")
        if not subtomo_dir.exists():
            self._tomo_list.set_choices([])
            self._text_edit.clear()
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
        if _is_2d(self._job_dir):
            _subtomo_label = "<b>Extracted 2D stacks (zero tilt)</b>"
        else:
            _subtomo_label = "<b>Extracted subtomograms (max projection)</b>"
        self._subtomo_label.setText(_subtomo_label)

        if (
            (t0 := time.time()) - self._last_force_reloaded > 5.0
            and self._tomo_list.current_text() == self._last_updated_dir
            and self._worker is None
        ):
            self._on_tomo_changed(self._tomo_list.current_row_texts())
            self._last_force_reloaded = t0

    def _on_tomo_changed(self, value: tuple[str, str] | None):
        if value is None:
            return
        tomo_name = value[0]
        self._subtomo_paths = _list_subtomo_names(self._job_dir, tomo_name)
        current_pos = self._slider.value()
        max_num = len(self._subtomo_paths)
        self._slider.setRange(0, max_num // self._num_page)
        current_pos = min(current_pos, self._slider.maximum())
        self._slider_value_changed(current_pos, udpate_slider=True)

    def _end_index(self, start: int) -> int:
        return min(start + self._num_page, len(self._subtomo_paths))

    def _slider_value_changed(self, value: int, *, udpate_slider: bool = False):
        # value: 0-indexed
        if udpate_slider:
            self._slider.setValue(value)
        start = value * self._num_page
        # Adjust for 1-based indexing
        self._slider_display_range.setText(f"{start + 1} - {self._end_index(start)}")
        self._plot_session_id = self._text_edit.prep_uuid()
        self.window_closed_callback()
        self._worker = self.plot_extracts(start, self._plot_session_id)
        self._start_worker()

    @thread_worker
    def plot_extracts(self, start_index: int, session: uuid.UUID):
        subtomo_dir = self._job_dir.resolve_path(self._tomo_list.current_text(1))
        yield self._clear_text, session
        for ith in range(start_index + 1, self._end_index(start_index) + 1):
            mrc_path = subtomo_dir / self._subtomo_paths[ith - 1]
            if not mrc_path.exists():
                img_str = self._text_edit.image_to_base64(
                    np.zeros((2, 2), dtype=np.float32), f"{ith}"
                )
                yield self._on_string_ready, (img_str, session)
                continue
            with mrcfile.mmap(mrc_path) as mrc:
                if ith == start_index + 1:  # first
                    angst = mrc.voxel_size.x
                    size = mrc.header.nx
                    msg = f"Image size: {size} pix ({size * angst:.1f} A)"
                    yield self._on_text_ready, (msg + "\n\n", session)
                if mrc.data.ndim != 3:
                    # this may happen if the subtomogram is being written right now
                    img_2d = mrc.data
                elif self._subtomo_paths[0].endswith("_stack2d.mrcs"):
                    img_2d = mrc.data[(mrc.data.shape[0] - 1) // 2, :, :]
                else:
                    img_2d = np.max(np.asarray(mrc.data), axis=0)
                img_2d = np.asarray(img_2d, dtype=np.float32)
                img_str = self._text_edit.image_to_base64(img_2d, f"{ith}", 0.2)
                yield self._on_string_ready, (img_str, session)
        if self._plot_session_id == session:
            self._worker = None

    def _clear_text(self, value: uuid.UUID):
        if value == self._plot_session_id:
            self._text_edit.clear()

    def _on_text_ready(self, value: tuple[str, uuid.UUID]):
        text, my_uuid = value
        if my_uuid != self._plot_session_id or self._worker is None:
            return
        self._text_edit.insertPlainText(text)

    def _on_string_ready(self, value: tuple[str, uuid.UUID]):
        img_str, my_uuid = value
        if my_uuid != self._plot_session_id or self._worker is None:
            return
        self._text_edit.insert_base64_image(img_str)


def _list_subtomo_names(job_dir: _job_dir.JobDirectory, tomoname: str) -> list[str]:
    tomo_dir = job_dir.path / "Subtomograms" / tomoname
    if _is_2d(job_dir):
        suffix = "_stack2d.mrcs"
    else:
        suffix = "_data.mrc"
    return [p for p in os.listdir(tomo_dir) if p.endswith(suffix)]


def _is_2d(job_dir: _job_dir.JobDirectory) -> bool:
    """Return whether the extraction is 2D stack or 3D subtomogram."""
    return job_dir.get_job_param("do_stack2d") == "Yes"
