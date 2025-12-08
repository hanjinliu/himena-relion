from __future__ import annotations
from pathlib import Path

import numpy as np
from qtpy import QtWidgets as QtW
import scipy.ndimage as ndi
from himena_relion._widgets import QJobScrollArea, Q2DViewer, register_job
from himena_relion import _job, _utils


@register_job(_job.AlignTiltSeriesJobDirectory)
class QAlignTiltSeriesViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job.AlignTiltSeriesJobDirectory = None
        layout = self._layout

        self._viewer = Q2DViewer(zlabel="Tilt index")
        self._ts_choice = QtW.QComboBox()
        self._ts_choice.currentTextChanged.connect(self._ts_choice_changed)
        layout.addWidget(QtW.QLabel("<b>Aligned tilt series</b>"))
        layout.addWidget(self._ts_choice)
        layout.addWidget(self._viewer)

    def on_job_updated(self, job_dir: _job.AlignTiltSeriesJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".xf":
            self._process_update(job_dir)

    def initialize(self, job_dir: _job.AlignTiltSeriesJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        self._process_update(job_dir)
        self._viewer.auto_fit()

    def _process_update(self, job_dir: _job.AlignTiltSeriesJobDirectory):
        choices: list[str] = []
        for imod_dir in job_dir.path.joinpath("external").glob("*"):
            if imod_dir.joinpath(f"{imod_dir.name}.xf").exists():
                choices.append(imod_dir.name)
        choices.sort()
        text = self._ts_choice.currentText()
        self._ts_choice.clear()
        self._ts_choice.addItems(choices)
        if text in choices:
            self._ts_choice.setCurrentText(text)
        elif choices == []:
            self._viewer.clear()

    def _ts_choice_changed(self, text: str):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        if job_dir is None:
            return

        xf = job_dir.xf_file(text)
        if not xf.exists():
            return

        # Don't use the tilt series inside IMOD project directories. They are redundant
        # and can be deleted by users after this job finished.
        pipeline = job_dir.parse_job_pipeline()
        if node := pipeline.get_input_by_type("TomogramGroupMetadata.star.relion"):
            tilt_job_dir = _job.JobDirectory.from_job_star(
                job_dir.relion_project_dir / node.path_job / "job.star"
            )
            for info in tilt_job_dir.iter_tilt_series():
                if info.tomo_name == text:
                    break
            else:
                raise ValueError(f"Tilt series {text} not found.")
            nbin = max(round(16 / info.tomo_tilt_series_pixel_size), 1)
            ts_view = info.read_tilt_series(job_dir.relion_project_dir)
            aligner = ImodImageAligner.from_xf(xf, nbin)
            self._viewer.set_array_view(ts_view.with_filter(aligner))


class ImodImageAligner:
    def __init__(self, components, nbin: int = 4):
        self._components: list[np.ndarray] = components
        self._nbin = nbin

    @classmethod
    def from_xf(cls, path: str | Path, nbin: int = 4) -> ImodImageAligner:
        """Create an ImodImageAligner from an IMOD .xf file."""
        components = []
        with open(path) as f:
            for line in f:
                vals = line.split()
                if len(vals) != 6:
                    raise ValueError("Invalid .xf file format.")
                a11, a12, a21, a22, dx, dy = map(float, vals)
                components.append(np.array([a11, a12, a21, a22, dx, dy]))
        return cls(components, nbin=nbin)

    def __call__(self, img: np.ndarray, i: int) -> np.ndarray:
        ny, nx = img.shape
        t = np.array(
            [[1, 0, ny // self._nbin / 2], [0, 1, nx // self._nbin / 2], [0, 0, 1]]
        )
        a11, a12, a21, a22, dx, dy = self._components[i]
        mat = np.array(
            [[a11, a21, dy / self._nbin], [a12, a22, dx / self._nbin], [0, 0, 1]]
        )
        mat = t @ np.linalg.inv(mat) @ np.linalg.inv(t)
        imgb = _utils.bin_image(img, self._nbin)
        cval = np.mean(imgb[::50])
        return ndi.affine_transform(imgb.astype(np.float32), mat, order=1, cval=cval)
