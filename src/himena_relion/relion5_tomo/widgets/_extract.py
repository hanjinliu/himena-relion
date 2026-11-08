from __future__ import annotations

import os
from pathlib import Path
import logging
import re
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
from himena_relion.consts import YES


_LOGGER = logging.getLogger(__name__)
_DIGITS = re.compile(r"(\d+)")


@register_job("relion.pseudosubtomo", is_tomo=True)
class QExtractJobViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir

        self._last_force_reloaded = -1.0
        self._num_page = 50
        # tomograms with updated subtomograms since the last reload
        self._updated_dirs: set[str] = set()
        # (subtomogram directory, file names) of the page currently shown, and whether
        # all the subtomograms in the page were completely loaded.
        self._plotted_page: tuple[str, tuple[str, ...]] | None = None
        self._plotted_page_complete = False
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
        self.on_job_files_updated(job_dir, [Path(path)])

    def on_job_files_updated(self, job_dir: _job_dir.JobDirectory, fps: list[Path]):
        """Handle a batch of changes to the job directory."""
        # Extraction writes thousands of subtomograms in a short time. Update the
        # widget only once for all of them.
        is_finished = False
        for fp in fps:
            if fp.name.startswith("RELION_JOB_"):
                is_finished = True
            elif fp.name.endswith(("_stack2d.mrcs", "_data.mrc")):
                self._updated_dirs.add(fp.parent.name)
        if is_finished or self._updated_dirs:
            self._update_tomo_list(force_reload=is_finished)
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        self._update_tomo_list()

    def _update_tomo_list(self, force_reload: bool = False):
        subtomo_dir = self._job_dir.path.joinpath("Subtomograms")
        if not subtomo_dir.exists():
            self._tomo_list.set_choices([])
            self._text_edit.clear()
            self._plotted_page = None
            return
        subtomo_dir_rel = self._job_dir.make_relative_path(subtomo_dir).as_posix()
        with os.scandir(subtomo_dir) as it:
            tomo_names = [
                (entry.name, f"{subtomo_dir_rel}/{entry.name}")
                for entry in it
                if entry.is_dir()
            ]
        tomo_names.sort(key=lambda x: x[0])
        if tomo_names != self._tomo_list._model._data:
            self._tomo_list.set_choices(tomo_names)
        if _is_2d(self._job_dir):
            _subtomo_label = "<b>Extracted 2D stacks (zero tilt)</b>"
        else:
            _subtomo_label = "<b>Extracted subtomograms (max projection)</b>"
        self._subtomo_label.setText(_subtomo_label)

        current = self._tomo_list.current_text()
        if (
            current in self._updated_dirs
            and time.time() - self._last_force_reloaded > 5.0
            and self._worker is None
        ) or force_reload:
            # Rescan the subtomograms. They are plotted again only if the page shown
            # is changed (see `_on_scanned`).
            self._updated_dirs.clear()
            self._last_force_reloaded = time.time()
            self._on_tomo_changed(self._tomo_list.current_row_texts(), force=False)
        elif current not in self._updated_dirs:
            # updates of other tomograms are not needed to be remembered
            self._updated_dirs.clear()

    def _on_tomo_changed(self, value: tuple[str, str] | None, force: bool = True):
        """Scan the subtomograms of the tomogram and plot them.

        If `force` is false, subtomograms are plotted only if the page shown is changed.
        """
        if value is None:
            return
        tomo_name = value[0]

        self.window_closed_callback()
        self._worker = self.scan_subtomos(tomo_name, force)
        self._start_worker()

    def _end_index(self, start: int) -> int:
        return min(start + self._num_page, len(self._subtomo_paths))

    def _page_key(self, value: int) -> tuple[str, tuple[str, ...]]:
        start = value * self._num_page
        return (
            self._tomo_list.current_text(1),
            tuple(self._subtomo_paths[start : self._end_index(start)]),
        )

    def _update_range_label(self, value: int):
        start = value * self._num_page
        # Adjust for 1-based indexing
        self._slider_display_range.setText(f"{start + 1} - {self._end_index(start)}")

    def _slider_value_changed(self, value: int, *, udpate_slider: bool = False):
        # value: 0-indexed
        if udpate_slider:
            self._slider.setValue(value)
        start = value * self._num_page
        self._update_range_label(value)
        self._plot_session_id = self._text_edit.prep_uuid()
        self.window_closed_callback()
        if self.isVisible():
            # Showing subtomograms is a very frequent operation and is usually heavy.
            self._plotted_page = self._page_key(value)
            self._plotted_page_complete = False
            self._worker = self.plot_extracts(
                self._job_dir.resolve_path(self._plotted_page[0]),
                self._plotted_page[1],
                start,
                self._plot_session_id,
            )
            self._start_worker()
        else:
            self._plotted_page = None

    @thread_worker
    def scan_subtomos(self, tomo_name: str, force: bool = True):
        subtomo_paths = _list_subtomo_names(self._job_dir, tomo_name)
        yield self._on_scanned, (subtomo_paths, force)

    @thread_worker
    def plot_extracts(
        self,
        subtomo_dir: Path,
        names: tuple[str, ...],
        start_index: int,
        session: uuid.UUID,
    ):
        yield self._clear_text, session
        is_complete = True
        is_first = True
        cutoff_rel = 1.0
        for ith, name in enumerate(names, start=start_index + 1):
            mrc_path = subtomo_dir / name
            if not mrc_path.exists():
                is_complete = False
                img_str = self._text_edit.image_to_base64(
                    np.zeros((2, 2), dtype=np.float32), f"{ith}"
                )
                yield self._on_string_ready, (img_str, session)
                continue
            with mrcfile.mmap(mrc_path) as mrc:
                if is_first:
                    is_first = False
                    angst = mrc.voxel_size.x
                    size = mrc.header.nx
                    msg = f"Image size: {size} pix ({size * angst:.1f} A)"
                    cutoff_rel = angst / 15.0  # 15 A cutoff
                    yield self._on_text_ready, (msg + "\n\n", session)
                if mrc.data.ndim != 3:
                    # this may happen if the subtomogram is being written right now
                    is_complete = False
                    img_2d = mrc.data
                elif name.endswith("_stack2d.mrcs"):
                    img_2d = mrc.data[(mrc.data.shape[0] - 1) // 2, :, :]
                else:
                    img_2d = np.max(np.asarray(mrc.data), axis=0)
                img_2d = np.asarray(img_2d, dtype=np.float32)
                img_str = self._text_edit.image_to_base64(img_2d, f"{ith}", cutoff_rel)
                yield self._on_string_ready, (img_str, session)
        # This must be done in the main thread after all the images are inserted.
        yield self._on_plot_finished, (is_complete, session)

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

    def _on_plot_finished(self, value: tuple[bool, uuid.UUID]):
        is_complete, my_uuid = value
        if my_uuid != self._plot_session_id:
            return
        self._plotted_page_complete = is_complete
        self._worker = None

    def _on_scanned(self, value: tuple[list[str], bool]):
        subtomo_paths, force = value
        self._subtomo_paths = subtomo_paths
        current_pos = self._slider.value()
        max_num = len(subtomo_paths)
        self._slider.setRange(0, max_num // self._num_page)
        current_pos = min(current_pos, self._slider.maximum())
        if (
            not force
            and self._plotted_page_complete
            and current_pos == self._slider.value()
            and self._plotted_page == self._page_key(current_pos)
        ):
            # Subtomograms in the current page are already shown. Plotting them again
            # is very heavy, so just update the slider.
            self._update_range_label(current_pos)
            self._worker = None
            return
        self._slider_value_changed(current_pos, udpate_slider=True)

    def showEvent(self, a0):
        self._on_tomo_changed(self._tomo_list.current_row_texts())
        return super().showEvent(a0)


def _list_subtomo_names(job_dir: _job_dir.JobDirectory, tomoname: str) -> list[str]:
    tomo_dir = job_dir.path / "Subtomograms" / tomoname
    if _is_2d(job_dir):
        suffix = "_stack2d.mrcs"
    else:
        suffix = "_data.mrc"
    if not tomo_dir.exists():
        return []
    # sort to keep the order of the subtomograms (os.listdir returns them in arbitrary
    # order), otherwise the page shown changes every time new subtomograms are written.
    return sorted(
        (p for p in os.listdir(tomo_dir) if p.endswith(suffix)), key=_natural_sort_key
    )


def _natural_sort_key(name: str) -> list[str | int]:
    """Sort key such that "2_data.mrc" comes before "10_data.mrc"."""
    return [int(s) if s.isdigit() else s for s in _DIGITS.split(name)]


def _is_2d(job_dir: _job_dir.JobDirectory) -> bool:
    """Return whether the extraction is 2D stack or 3D subtomogram."""
    params = job_dir.get_job_params_as_dict()
    if "do_stack2d" in params:
        return params["do_stack2d"] == YES
    elif "subtomo_format" in params:
        return params["subtomo_format"] == "2D stacks"
    return True
