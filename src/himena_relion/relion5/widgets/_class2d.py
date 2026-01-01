from __future__ import annotations
import logging
from pathlib import Path
import uuid
import mrcfile
import numpy as np
from starfile_rs import read_star
from superqt.utils import thread_worker
from qtpy import QtWidgets as QtW, QtCore
from himena_relion._widgets import (
    QJobScrollArea,
    QIntChoiceWidget,
    register_job,
    QImageViewTextEdit,
    QNumParticlesLabel,
)
from himena_relion._utils import get_subset_sizes, wait_for_file
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job("relion.class2d")
class QClass2DViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout
        self._sort_by = QtW.QComboBox()
        self._sort_by.addItems(["Index", "Particle number", "Resolution"])
        self._sort_by.setCurrentIndex(1)
        self._sort_by.setFixedWidth(120)
        self._text_edit = QImageViewTextEdit()
        self._text_edit.setMinimumHeight(360)
        self._iter_choice = QIntChoiceWidget("Iteration", label_width=60)
        self._num_subsets_label = QNumParticlesLabel()

        self._iter_choice.current_changed.connect(self._iter_changed)
        self._sort_by.currentIndexChanged.connect(self._sort_by_changed)
        layout.addWidget(QtW.QLabel("<b>2D Classes</b>"))
        hlayout = QtW.QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        label = QtW.QLabel("Sort by:")
        label.setMaximumWidth(80)
        hlayout.addWidget(label)
        hlayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        hlayout.addWidget(self._sort_by)
        layout.addLayout(hlayout)
        layout.addWidget(self._text_edit)
        hlayout = QtW.QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(self._iter_choice)
        hlayout.addWidget(self._num_subsets_label)
        layout.addLayout(hlayout)
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

    def _sort_by_changed(self):
        self._iter_changed(self._iter_choice.value())

    def _iter_changed(self, value: int):
        self.window_closed_callback()
        self._text_edit.clear()
        try:
            path_optimiser = self._job_dir.path / f"run_it{value:0>3}_optimiser.star"
            size, fin_size = get_subset_sizes(path_optimiser)
        except Exception:
            size, fin_size = -1, -1
        self._num_subsets_label.set_subset_sizes(size, fin_size)
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
        if not wait_for_file(path_model):
            _LOGGER.error("Failed to find %s", path_model)
            return
        df = read_star(path_model)["model_classes"].trust_loop().to_pandas()
        dist_percent = df["rlnClassDistribution"] * 100
        resolutions = df["rlnEstimatedResolution"]
        # sorting
        if self._sort_by.currentIndex() == 1:
            sort_indices = np.argsort(-dist_percent.values)
        elif self._sort_by.currentIndex() == 2:
            sort_indices = np.argsort(resolutions.values)
        else:
            sort_indices = np.arange(len(dist_percent))
        for ith in sort_indices:
            distribution = dist_percent.iloc[ith]
            resolution = resolutions.iloc[ith]
            img_slice = img[ith]
            text = f"{ith + 1}\n{distribution:.2f}%\n{resolution:.1f} A"
            img_str = self._text_edit.image_to_base64(img_slice, text)
            yield img_str, session

    def _on_class_yielded(self, value: tuple[str, uuid.UUID]):
        if self._worker is None:
            return
        img_str, my_uuid = value
        if my_uuid != self._plot_session_id:
            return
        self._text_edit.insert_base64_image(img_str)
