from __future__ import annotations
import logging
from pathlib import Path
import mrcfile
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from io import BytesIO
import base64
from starfile_rs import read_star
from superqt.utils import thread_worker, GeneratorWorker
from qtpy import QtWidgets as QtW
from himena_relion._widgets import (
    QJobScrollArea,
    QIntChoiceWidget,
    register_job,
)
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job("relion.class2d")
class QManualPickViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._text_edit = QtW.QTextEdit()
        self._text_edit.setReadOnly(True)
        self._iter_choice = QIntChoiceWidget("Iteration", label_width=60)

        self._iter_choice.current_changed.connect(self._iter_changed)
        self._worker: GeneratorWorker | None = None
        layout.addWidget(QtW.QLabel("<b>2D Classes</b>"))
        layout.addWidget(self._text_edit)
        layout.addWidget(self._iter_choice)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".mrcs":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        niters: list[int] = []
        for path in job_dir.path.glob("run_it*_classes.mrcs"):
            try:
                iter_num = int(path.stem[6:-8])
            except Exception:
                continue
            else:
                niters.append(iter_num)
        niters.sort()
        self._iter_choice.set_choices(niters)
        self._iter_changed(niters[-1] if niters else 0)

    def _iter_changed(self, value: int):
        self.window_closed_callback()
        self._text_edit.clear()
        self._worker = self.plot_classes(value)
        self._worker.yielded.connect(self._on_class_yielded)
        self._worker.start()

    @thread_worker
    def plot_classes(self, niter: int):
        path_img = self._job_dir.path / f"run_it{niter:03d}_classes.mrcs"
        path_model = self._job_dir.path / f"run_it{niter:03d}_model.star"
        with mrcfile.open(path_img) as mrc:
            img = np.asarray(mrc.data)
        df = read_star(path_model)["model_classes"].trust_loop().to_pandas()
        dist_percent = df["rlnClassDistribution"] * 100
        resolutions = df["rlnEstimatedResolution"]
        for ith, img_slice in enumerate(img):
            distribution = dist_percent.iloc[ith]
            resolution = resolutions.iloc[ith]
            img_slice_256 = ndi.zoom(img_slice, 256 / img_slice.shape[0], order=1)
            img_slice_normed = (
                (img_slice_256 - img_slice_256.min())
                / (img_slice_256.max() - img_slice_256.min())
                * 255
            )
            img_slice = img_slice_normed.astype(np.uint8)

            pil_img = Image.fromarray(img_slice).convert("RGB")
            draw = ImageDraw.Draw(pil_img)
            text = f"Class {ith + 1}\n{distribution:.1f}%\n{resolution:.1f} A"
            draw.text((5, 5), text, fill=(0, 255, 0))

            buffer = BytesIO()
            pil_img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()
            yield img_str, ith

    def _on_class_yielded(self, img_str: str, ith: int):
        self._text_edit.append(f'<img src="data:image/png;base64,{img_str}"/><br>')
        if ith % 10 == 9:
            self._text_edit.append("<br>")

    def window_closed_callback(self):
        if self._worker:
            self._worker.quit()
            self._worker = None

    def closeEvent(self, a0):
        self.window_closed_callback()
        return super().closeEvent(a0)
