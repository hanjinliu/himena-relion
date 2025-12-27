from __future__ import annotations
from pathlib import Path
import logging
import mrcfile
import numpy as np
import base64
from io import BytesIO
from PIL import Image
from qtpy import QtWidgets as QtW, QtGui
from starfile_rs import read_star, read_star_block
from scipy import ndimage as ndi
from superqt.utils import thread_worker, GeneratorWorker

from himena_relion._widgets import QJobScrollArea, register_job
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


class QSelectJobBase(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job_dir.SelectInteractiveJobDirectory = None
        self._text_edit = QtW.QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self._layout.addWidget(self._text_edit)
        self._worker: GeneratorWorker | None = None

    def initialize(self, job_dir: _job_dir.SelectInteractiveJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        self._text_edit.clear()
        self._text_edit.setFixedHeight(400)
        if self._worker:
            self._worker.quit()
        self._worker = thread_worker(self.insert_html)(job_dir)
        self._worker.yielded.connect(self._cb_html_requested)
        self._worker.start()

    def insert_html(self, job_dir: _job_dir.SelectInteractiveJobDirectory):
        """Insert HTML into the text edit.

        This is a generator function that yields HTML strings or np.ndarray tables.
        """
        # implement this in the subclass
        yield ""

    def on_job_updated(self, job_dir: _job_dir.RemoveDuplicatesJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix not in [".out", ".err", ".star"]:
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def _print_running(self):
        self._text_edit.setText("Job is running...")

    def _print_file_broken(self):
        self._text_edit.setText("Output file is broken or missing.")

    def _get_summary_table(
        self, n_selected: int, n_removed: int, n_all: int
    ) -> np.ndarray:
        data = np.array(
            [
                ["Selected", str(n_selected), f"{n_selected / n_all:.2%}"],
                ["Removed", str(n_removed), f"{n_removed / n_all:.2%}"],
                ["Total", str(n_all), "100%"],
            ],
            dtype=np.dtypes.StringDType(),
        )
        return data

    def _cb_html_requested(self, html):
        """Handle HTML requested signal."""
        cursor = self._text_edit.textCursor()
        if isinstance(html, str):
            cursor.insertHtml(html)
        elif isinstance(html, np.ndarray):
            nrow, ncol = html.shape
            if texttable := cursor.insertTable(nrow, ncol):
                for i in range(nrow):
                    for j in range(ncol):
                        texttable.cellAt(i, j).firstCursorPosition().insertText(
                            str(html[i, j])
                        )
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            cursor.insertText("\n\n")


@register_job(_job_dir.RemoveDuplicatesJobDirectory)
class QRemoveDuplicatesViewer(QSelectJobBase):
    def insert_html(self, job_dir: _job_dir.RemoveDuplicatesJobDirectory):
        """Initialize the viewer with the job directory."""
        path_sel = job_dir.particles_star()
        path_rem = job_dir.particles_removed_star()
        if not (path_sel.exists() and path_rem.exists()):
            return "Not enough output files to display results."
        yield "<h2>Summary</h2>"
        try:
            block_selected = read_star_block(path_sel, "particles").trust_loop()
            block_removed = read_star(path_rem).first().trust_loop()
        except Exception:
            return "Output file is broken or missing."
        n_selected = len(block_selected)
        n_removed = len(block_removed)
        n_all = n_selected + n_removed
        yield self._get_summary_table(n_selected, n_removed, n_all)


@register_job(_job_dir.SelectInteractiveJobDirectory)
class QSelectInteractiveViewer(QSelectJobBase):
    def insert_html(self, job_dir: _job_dir.SelectInteractiveJobDirectory):
        path_all = job_dir.particles_pre_star()
        path_sel = job_dir.particles_star()
        if path_all is None or not (path_sel.exists() and path_all.exists()):
            return "Not enough output files to display results."
        yield "<h2>Summary</h2>"
        try:
            block_all = read_star_block(path_all, "particles").trust_loop()
            block_selected = read_star_block(path_sel, "particles").trust_loop()
        except Exception:
            return "Output file is broken or missing."
        n_all = len(block_all)
        if n_all == 0:
            return
        n_selected = len(block_selected)
        n_removed = n_all - n_selected

        yield self._get_summary_table(n_selected, n_removed, n_all)

        is_selected = job_dir.is_selected_array()
        if is_selected is None:
            return

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

        yield "<h2>Selected Images</h2><br>"
        yield from yield_projections(images_selected)
        yield "<br><h2>Removed Images</h2><br>"
        yield from yield_projections(images_removed)


@register_job(_job_dir.SplitParticlesJobDirectory)
class SplitParticlesViewer(QSelectJobBase):
    def insert_html(self, job_dir: _job_dir.SplitParticlesJobDirectory):
        for path in job_dir.iter_particles_stars():
            if not path.exists():
                continue
            block = read_star(path).first().trust_loop()
            yield f"<h2>{path.name} = {len(block)} particles</h2>"
            df = block.to_pandas()
            particles_in_each_tomo = []
            for name, sub in df.groupby("rlnTomoName"):
                particles_in_each_tomo.append((name, f"n = {sub.shape[0]}"))
            particles_in_each_tomo.sort(key=lambda x: x[0])
            yield np.array(particles_in_each_tomo, dtype=np.dtypes.StringDType())
            yield "<br><br>"


def yield_projections(images: list[tuple[Path, np.ndarray | None]]):
    for path, img in images:
        pathname = "/".join(path.parts[-3:])
        yield f"<b>{pathname}</b><br>"
        if img is None:
            yield "No Image<br>"
        else:
            for axis in range(3):
                proj = img.max(axis=axis)

                pil_img = Image.fromarray(proj)
                buffer = BytesIO()
                pil_img.save(buffer, format="PNG")
                img_str = base64.b64encode(buffer.getvalue()).decode()
                yield f'<img src="data:image/png;base64,{img_str}"/>'

            yield "<br>"
