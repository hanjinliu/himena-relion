from __future__ import annotations
import logging
from pathlib import Path
import uuid
import mrcfile
import numpy as np
from starfile_rs import read_star
from superqt.utils import thread_worker, GeneratorWorker
from qtpy import QtWidgets as QtW
from himena_relion._widgets import (
    QJobScrollArea,
    QIntChoiceWidget,
    register_job,
)
from ._shared import QImageViewTextEdit
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job("relion.class2d")
class QClass2DViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._text_edit = QImageViewTextEdit()
        self._iter_choice = QIntChoiceWidget("Iteration", label_width=60)

        self._iter_choice.current_changed.connect(self._iter_changed)
        self._worker: GeneratorWorker | None = None
        layout.addWidget(QtW.QLabel("<b>2D Classes</b>"))
        layout.addWidget(self._text_edit)
        layout.addWidget(self._iter_choice)

        self._plot_session_id = self._text_edit.prep_uuid()

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

    def _iter_changed(self, value: int):
        self.window_closed_callback()
        self._text_edit.clear()
        self._plot_session_id = self._text_edit.prep_uuid()
        self._worker = self.plot_classes(value, self._plot_session_id)
        self._worker.yielded.connect(self._on_class_yielded)
        self._worker.start()

    @thread_worker
    def plot_classes(self, niter: int, session: uuid.UUID):
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
            text = f"{ith + 1}\n{distribution:.1f}%\n{resolution:.1f} A"
            img_str = self._text_edit.image_to_base64(img_slice, text)
            yield img_str, session

    def _on_class_yielded(self, value: tuple[str, uuid.UUID]):
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
