from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator
import uuid
import mrcfile
import mrcfile.mrcmemmap
import polars as pl
import numpy as np
from qtpy import QtWidgets as QtW, QtCore
import logging
from starfile_rs import read_star
from superqt.utils import thread_worker
from himena.qt._qlineedit import QDoubleLineEdit
from himena_builtins.qt.widgets._shared import labeled
from himena_relion import _job_dir
from himena_relion._widgets import (
    QJobScrollArea,
    register_job,
    QImageViewTextEdit,
)

_LOGGER = logging.getLogger(__name__)


@register_job("relion.subtract")
class QSubtractViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout
        self._num_page = 20
        self._num_part_label = QtW.QLabel(" --- particles")
        self._text_edit = QImageViewTextEdit(font_size=11)
        self._text_edit.setMinimumHeight(350)
        self._lowpass_cutoff = QDoubleLineEdit("10.0")
        self._lowpass_cutoff.setMinimum(0.0)
        self._lowpass_cutoff.setMaximum(200.0)
        self._lowpass_cutoff.setFixedWidth(40)
        self._slider = QtW.QSlider(QtCore.Qt.Orientation.Horizontal)
        self._slider_display_range = QtW.QLabel("?? - ??")
        layout.addWidget(QtW.QLabel("<b>&#9679; Subtracted particles</b>"))
        hlayout = QtW.QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(QtW.QLabel("Display Range:"))
        hlayout.addWidget(self._slider)
        hlayout.addWidget(self._slider_display_range)

        layout.addLayout(hlayout)
        layout.addWidget(self._text_edit)
        hlayout2 = QtW.QHBoxLayout()
        hlayout2.setContentsMargins(0, 0, 0, 0)
        hlayout2.addWidget(labeled("Lowpass cutoff (A):", self._lowpass_cutoff))
        hlayout2.addStretch()
        hlayout2.addWidget(self._num_part_label)
        layout.addLayout(hlayout2)
        self._slider.valueChanged.connect(self._slider_value_changed)
        self._lowpass_cutoff.valueChanged.connect(
            lambda: self._slider_value_changed(
                self._slider.value(), update_slider=False
            )
        )
        self._plot_session_id = self._text_edit.prep_uuid()
        self._image_sub = pl.Series("rlnImageName", [], dtype=pl.String)
        self._image_orig = pl.Series("rlnImageOriginalName", [], dtype=pl.String)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == "particle_subtracted.star":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        star_path = job_dir.path / "particles_subtracted.star"
        if not star_path.exists():
            self._text_edit.setPlainText("particle_subtracted.star not created yet.")
            return

        if particles_block := read_star(star_path).get("particles"):
            df = particles_block.to_polars()

            self._image_sub = df["rlnImageName"]
            self._image_orig = df["rlnImageOriginalName"]
            self._slider.setRange(
                0, max(0, self._image_sub.len() - 1) // self._num_page
            )
            self._slider_value_changed(0, update_slider=True)
        else:
            self._text_edit.setPlainText("No 'particles' block found in the star file.")

        num_total = self._image_orig.len()
        self._num_part_label.setText(f"Total: <b>{num_total}</b> particles")

    def _slider_value_changed(self, value: int, *, update_slider: bool = False):
        # value: 0-indexed
        self.window_closed_callback()
        if update_slider:
            self._slider.setValue(value)
        self._text_edit.clear()
        self._plot_session_id = self._text_edit.prep_uuid()
        start = value * self._num_page
        # Adjust for 1-based indexing
        self._slider_display_range.setText(
            f"{start + 1} - {min(start + self._num_page, self._image_orig.len())}"
        )
        if self.isVisible():
            self._worker = self.plot_extracts(start, self._plot_session_id)
            self._start_worker()

    @thread_worker
    def plot_extracts(self, start_index: int, session: uuid.UUID):
        end_index = min(start_index + self._num_page, self._image_orig.len() + 1)
        sl = slice(start_index, end_index)
        first = True

        try:
            cutoff_a = float(self._lowpass_cutoff.text())
        except ValueError:
            return
        for (mrc_orig, img_orig), (_, img_sub), ith in zip(
            read_mrc_slices(self._image_orig[sl], self._job_dir),
            read_mrc_slices(self._image_sub[sl], self._job_dir),
            range(start_index + 1, end_index + 1),
            strict=False,
        ):
            if first:
                angst = mrc_orig.voxel_size.x
                size = mrc_orig.header.nx
                msg = f"Image size: {size} pix ({size * angst:.1f} A)\nBefore --> After subtraction"
                cutoff_rel = angst / cutoff_a
                first = False
                yield self._on_text_ready, (msg + "\n\n", session)

            img_str_ori = self._text_edit.image_to_base64(
                img_orig, f"{ith}", cutoff_rel
            )
            yield self._on_string_ready, (img_str_ori, session)
            yield self._on_text_ready, (" -> ", session)
            img_str_sub = self._text_edit.image_to_base64(img_sub, "", cutoff_rel)
            yield self._on_string_ready, (img_str_sub, session)
            yield self._on_text_ready, ("\n", session)

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

    def showEvent(self, a0):
        self._slider_value_changed(self._slider.value(), update_slider=False)
        return super().showEvent(a0)


def read_mrc_slices(
    entries: Iterable[str],
    jobdir: _job_dir.JobDirectory,
) -> Iterator[tuple[mrcfile.mrcmemmap.MrcMemmap, np.ndarray]]:
    last_path = ""
    mrc = None
    for line in entries:
        ith, path = line.split("@")
        ith = int(ith)
        if path != last_path or mrc is None:
            last_path = path
            mrc = mrcfile.mmap(jobdir.resolve_path(path))
        yield mrc, np.asarray(mrc.data[ith - 1], dtype=np.float32)
