from __future__ import annotations
from pathlib import Path
import logging
import mrcfile
import numpy as np
from qtpy import QtGui
from starfile_rs import read_star, read_star_block
from superqt.utils import thread_worker

from himena_relion._widgets import QJobScrollArea, register_job, QImageViewTextEdit
from himena_relion import _job_dir
from himena_relion.schemas import ModelClasses

_LOGGER = logging.getLogger(__name__)


class QSelectJobBase(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        self._text_edit = QImageViewTextEdit()
        self._layout.addWidget(self._text_edit)

    def initialize(self, job_dir: _job_dir.SelectInteractiveJobDirectory):
        """Initialize the viewer with the job directory."""
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


@register_job("relion.select.removeduplicates")
class QRemoveDuplicatesViewer(QSelectJobBase):
    def insert_html(self, job_dir: _job_dir.RemoveDuplicatesJobDirectory):
        """Initialize the viewer with the job directory."""
        path_sel = job_dir.particles_star()
        path_rem = job_dir.particles_removed_star()
        if not (path_sel.exists() and path_rem.exists()):
            return _NOT_ENOUGH_MSG
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


@register_job("relion.select.interactive")
@register_job("relion.select.class2dauto")
class QSelectInteractiveViewer(QSelectJobBase):
    def insert_html(self, job_dir: _job_dir.SelectInteractiveJobDirectory):
        is_2d = job_dir.path.joinpath("class_averages.star").exists()
        if is_2d:
            yield from self._insert_html_class2d(job_dir)
        else:
            yield from self._insert_html_class3d(job_dir)

    def _insert_html_class2d(self, job_dir: _job_dir.SelectInteractiveJobDirectory):
        class_avg_path = job_dir.path.joinpath("class_averages.star")
        if not class_avg_path.exists():
            yield _NOT_ENOUGH_MSG
            return
        path_all = job_dir.particles_pre_star()
        path_sel = job_dir.particles_star()
        if path_all is None or not (path_sel.exists() and path_all.exists()):
            yield _NOT_ENOUGH_MSG
            return
        model = ModelClasses.validate_file(class_avg_path)
        class2d_path = model.ref_image[0].split("@")[1]
        class2d_selected = {int(_id.split("@")[0]) - 1 for _id in model.ref_image}

        with mrcfile.open(self._job_dir.resolve_path(class2d_path)) as mrc:
            class2d_arr = np.asarray(mrc.data, dtype=np.float32)

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

        # print selected and removed HTML images in the text edit
        images_selected: list[tuple[np.ndarray, str]] = []
        images_removed: list[tuple[np.ndarray, str]] = []
        for ith in range(len(class2d_arr)):
            img = class2d_arr[ith]
            if ith in class2d_selected:
                images_selected.append((img, str(ith)))
            else:
                images_removed.append((img, str(ith)))

        for images, msg in [
            (images_selected, "<h2>Selected Images</h2><br>"),
            (images_removed, "<br><h2>Removed Images</h2><br>"),
        ]:
            yield msg
            for img, text in images:
                img_str = self._text_edit.image_to_base64(img, text)
                yield f'<img src="data:image/png;base64,{img_str}"/>'

    def _insert_html_class3d(self, job_dir: _job_dir.SelectInteractiveJobDirectory):
        path_all = job_dir.particles_pre_star()
        path_sel = job_dir.particles_star()
        if path_all is None or not (path_sel.exists() and path_all.exists()):
            yield _NOT_ENOUGH_MSG
            return
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

        # print selected and removed HTML images in the text edit
        images_selected: list[tuple[str, np.ndarray]] = []
        images_removed: list[tuple[str, np.ndarray]] = []
        texts = ["XY", "XZ", "YZ"]
        for path, is_sel in zip(job_dir.class_map_paths(is_selected.size), is_selected):
            if path is not None:
                with mrcfile.open(path) as mrc:
                    array = np.asarray(mrc.data)
            else:
                array = None
            path_rel = job_dir.make_relative_path(path)
            if is_sel:
                images_selected.append((path_rel, array))
            else:
                images_removed.append((path_rel, array))

        for images, msg in [
            (images_selected, "<h2>Selected Images</h2><br>"),
            (images_removed, "<br><h2>Removed Images</h2><br>"),
        ]:
            yield msg
            for path, array in images:
                yield f"<b>{path}</b><br>"
                if array is None:
                    yield "No image data."
                else:
                    for axis in range(3):
                        proj = self._text_edit.image_to_base64(
                            array.max(axis=axis), texts[axis]
                        )
                        yield f'<img src="data:image/png;base64,{proj}"/>'
                yield "<br>"


@register_job("relion.select.split")
class SplitParticlesViewer(QSelectJobBase):
    def insert_html(self, job_dir: _job_dir.SplitParticlesJobDirectory):
        for path in job_dir.iter_particles_stars():
            if not path.exists():
                continue
            block = read_star(path).first().trust_loop()
            yield f"<h2>{path.name} = {len(block)} particles</h2>"
            df = block.to_pandas()
            particles_in_each_set = []
            for col in ["rlnTomoName", "rlnMicrographName"]:
                # tomo or SPA
                if col in df.columns:
                    for name, sub in df.groupby(col):
                        particles_in_each_set.append((name, f"n = {sub.shape[0]}"))
                    particles_in_each_set.sort(key=lambda x: x[0])
                    yield np.array(particles_in_each_set, dtype=np.dtypes.StringDType())
                    yield "<br><br>"


@register_job("relion.select.onvalue")
class SelectOnValueViewer(QSelectJobBase):
    def insert_html(self, job_dir: _job_dir.JobDirectory):
        path_mic = job_dir.path / "micrographs.star"
        path_particles = job_dir.path / "particles.star"
        job_params = job_dir.get_job_params_as_dict()
        if path_mic.exists() and (fn := job_params.get("fn_mic")):
            # this is split-micrograph job
            block_name = "micrographs"
        elif path_particles.exists() and (fn := job_params.get("fn_data")):
            # this is split-particle job
            block_name = "particles"
        else:
            yield "Not supported job output."
            return
        loop = read_star_block(fn, block_name).trust_loop()
        loop_pre = read_star_block(fn, block_name).trust_loop()
        n_selected = len(loop)
        n_removed = len(loop_pre) - n_selected
        yield self._get_summary_table(n_selected, n_removed, n_selected + n_removed)


_NOT_ENOUGH_MSG = "Not enough output files to display results."
