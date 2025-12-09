from __future__ import annotations
from pathlib import Path
import logging
import mrcfile
import numpy as np
from qtpy import QtWidgets as QtW, QtGui
import starfile
from scipy import ndimage as ndi
from himena_relion._widgets import QJobScrollArea, register_job
from himena_relion import _job
import base64
from io import BytesIO
from PIL import Image

_LOGGER = logging.getLogger(__name__)


class QSelectJobBase(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job.SelectInteractiveJobDirectory = None
        self._text_edit = QtW.QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self._layout.addWidget(self._text_edit)

    def on_job_updated(self, job_dir: _job.RemoveDuplicatesJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix not in [".out", ".err", ".star"]:
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_id)

    def _print_running(self):
        self._text_edit.setText("Job is running...")

    def _print_file_broken(self):
        self._text_edit.setText("Output file is broken or missing.")

    def _print_summary_table(self, n_selected: int, n_removed: int, n_all: int):
        cursor = self._text_edit.textCursor()
        if texttable := cursor.insertTable(3, 3):
            texttable.cellAt(0, 0).firstCursorPosition().insertText("Selected")
            texttable.cellAt(0, 1).firstCursorPosition().insertText(str(n_selected))
            texttable.cellAt(0, 2).firstCursorPosition().insertText(
                f"{n_selected / n_all:.2%}"
            )
            texttable.cellAt(1, 0).firstCursorPosition().insertText("Removed")
            texttable.cellAt(1, 1).firstCursorPosition().insertText(str(n_removed))
            texttable.cellAt(1, 2).firstCursorPosition().insertText(
                f"{n_removed / n_all:.2%}"
            )
            texttable.cellAt(2, 0).firstCursorPosition().insertText("Total")
            texttable.cellAt(2, 1).firstCursorPosition().insertText(str(n_all))
            texttable.cellAt(2, 2).firstCursorPosition().insertText("100%")
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.insertText("\n\n")


@register_job(_job.RemoveDuplicatesJobDirectory)
class QRemoveDuplicatesViewer(QSelectJobBase):
    def initialize(self, job_dir: _job.RemoveDuplicatesJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        self._text_edit.clear()
        self._text_edit.setFixedHeight(220)
        path_sel = job_dir.particles_star()
        path_rem = job_dir.particles_removed_star()
        if not (path_sel.exists() and path_rem.exists()):
            return self._print_running()
        df_selected = starfile.read(path_sel, always_dict=True).get("particles", None)
        if df_selected is None:
            return self._print_file_broken()
        df_removed = starfile.read(path_rem)
        if df_removed is None:
            return self._print_file_broken()
        n_selected = df_selected.shape[0]
        n_removed = df_removed.shape[0]
        n_all = n_selected + n_removed
        self._print_summary_table(n_selected, n_removed, n_all)


@register_job(_job.SelectInteractiveJobDirectory)
class QSelectInteractiveViewer(QSelectJobBase):
    def initialize(self, job_dir: _job.SelectInteractiveJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir

        self._text_edit.clear()
        self._text_edit.setFixedHeight(400)
        path_all = job_dir.particles_pre_star()
        path_sel = job_dir.particles_star()

        df_all = starfile.read(path_all, always_dict=True).get("particles", None)
        if df_all is None:
            return self._print_file_broken()
        df_selected = starfile.read(path_sel, always_dict=True).get("particles", None)
        if df_selected is None:
            return self._print_file_broken()
        n_all = df_all.shape[0]
        if n_all == 0:
            return
        n_selected = df_selected.shape[0]
        n_removed = n_all - n_selected
        cursor = self._text_edit.textCursor()

        cursor.insertHtml("<h2>Summary</h2>")
        self._print_summary_table(n_selected, n_removed, n_all)

        is_selected = job_dir.is_selected_array()
        if is_selected is None:
            return self._print_file_broken()

        # print selected and removed images in the text edit
        images_selected: list[tuple[Path, np.ndarray | None]] = []
        images_removed: list[tuple[Path, np.ndarray | None]] = []
        for path, is_sel in zip(job_dir.class_map_paths(is_selected.size), is_selected):
            if path is not None:
                with mrcfile.open(path) as mrc:
                    array = np.asarray(mrc.data)
                # Calculate zoom factor to rescale to 128x128
                current_shape = array.shape
                zoom_factor = [96 / s for s in current_shape]
                array = ndi.zoom(array, zoom_factor, order=1)
                min0, max0 = array.min(), array.max()
                _array_rescaled = (
                    (array.clip(min0, max0) - min0) / (max0 - min0) * 255.0
                )
                array = _array_rescaled.astype(np.uint8)
            else:
                array = None
            if is_sel:
                images_selected.append((path, array))
            else:
                images_removed.append((path, array))

        cursor.insertHtml("<h2>Selected Images</h2><br>")
        print_projections(cursor, images_selected)
        cursor.insertHtml("<br><h2>Removed Images</h2><br>")
        print_projections(cursor, images_removed)


def print_projections(
    cursor: QtGui.QTextCursor, images: list[tuple[Path, np.ndarray | None]]
):
    for path, img in images:
        pathname = "/".join(path.parts[-3:])
        cursor.insertHtml(f"<b>{pathname}</b><br>")
        if img is None:
            cursor.insertText("No Image<br>")
        else:
            for axis in range(3):
                proj = img.max(axis=axis)

                pil_img = Image.fromarray(proj)
                buffer = BytesIO()
                pil_img.save(buffer, format="PNG")
                img_str = base64.b64encode(buffer.getvalue()).decode()
                cursor.insertHtml(f'<img src="data:image/png;base64,{img_str}"/>')

            cursor.insertHtml("<br>")
