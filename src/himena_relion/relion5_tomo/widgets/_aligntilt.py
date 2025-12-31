from __future__ import annotations
from pathlib import Path
import logging
import numpy as np

import pandas as pd
from qtpy import QtWidgets as QtW, QtGui, QtCore
import scipy.ndimage as ndi
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    register_job,
    QMicrographListWidget,
)
from himena_relion import _job_dir, _utils
from himena_relion.schemas import TSAlignModel

_LOGGER = logging.getLogger(__name__)


@register_job("relion.aligntiltseries", is_tomo=True)
class QAlignTiltSeriesViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.AlignTiltSeriesJobDirectory):
        super().__init__()
        self._job_dir = _job_dir.AlignTiltSeriesJobDirectory(job_dir.path)
        layout = self._layout

        self._viewer = Q2DViewer(zlabel="Tilt index")
        self._viewer.setMinimumHeight(480)
        self._ts_list = QMicrographListWidget(["Tilt Series"])
        self._ts_list.current_changed.connect(self._ts_choice_changed)
        self._current_ts_align: pd.DataFrame | None = None
        self._batchruntomo_log = QBatchruntomoLog()
        layout.addWidget(self._ts_list)
        layout.addWidget(QtW.QLabel("<b>Aligned tilt series</b>"))
        layout.addWidget(self._viewer)
        layout.addWidget(QtW.QLabel("<b>Batchruntomo Log</b>"))
        layout.addWidget(self._batchruntomo_log)

    def on_job_updated(self, job_dir, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".xf":
            self.initialize(self._job_dir)
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def initialize(self, job_dir):
        """Initialize the viewer with the job directory."""
        choices: list[str] = []
        for imod_dir in job_dir.path.joinpath("external").glob("*"):
            if imod_dir.joinpath(f"{imod_dir.name}.xf").exists():
                choices.append((imod_dir.name,))
        choices.sort(key=lambda x: x[0])
        self._ts_list.set_choices(choices)
        if len(choices) == 0:
            self._viewer.clear()

    def _ts_choice_changed(self, texts: tuple[str, ...]):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        text = texts[0]
        xf = job_dir.xf_file(text)
        if not xf.exists():
            return

        # Don't use the tilt series inside IMOD project directories. They are redundant
        # and can be deleted by users after this job finished.
        pipeline = job_dir.parse_job_pipeline()
        if node := pipeline.get_input_by_type("TomogramGroupMetadata"):
            _LOGGER.debug("Found input: %s", node.path)
            tilt_job_dir = _job_dir.JobDirectory.from_job_star(
                job_dir.resolve_path(node.path_job / "job.star")
            )
            for info in tilt_job_dir.iter_tilt_series():
                if info.tomo_name == text:
                    break
            else:
                raise ValueError(f"Tilt series {text} not found.")
            nbin = max(round(16 / info.tomo_tilt_series_pixel_size), 1)
            ts_view = info.read_tilt_series(job_dir.relion_project_dir)
            aligner = ImodImageAligner.from_xf(xf, nbin)
            self._udpate_fiducials(text, aligner)

            self._viewer.set_array_view(ts_view.with_filter(aligner.transform_image))

        # update current TS_XX.star content
        ts_star = self._job_dir.path / "tilt_series" / f"{text}.star"
        if ts_star.exists():
            try:
                self._current_ts_align = TSAlignModel.validate_file(ts_star)
            except Exception:
                self._current_ts_align = None

        # update batchruntomo log
        log_file = job_dir.path / "external" / text / "batchruntomo.log"
        if log_file.exists():
            self._batchruntomo_log.setPlainText(log_file.read_text())

    def _udpate_fiducials(self, text: str, aligner: ImodImageAligner):
        # if tracked fiducials are available, display them
        # return
        # BUG: not aligned well
        import imodmodel

        job_dir = self._job_dir
        if (fid_path := job_dir.fid_file(text)).exists() and (
            params := job_dir.image_shape_params(text)
        ):
            _LOGGER.debug("Fiducial file %s found. Load it.", fid_path)
            fid = imodmodel.read(fid_path)[["z", "y", "x"]].to_numpy(dtype=np.float32)
            nbin_prealign, ny, nx = params
            fid[:, 1:3] *= nbin_prealign
            fid[:, 1] -= (ny - 1) / 2
            fid[:, 2] -= (nx - 1) / 2
            fid_tr = aligner.transform_points(fid, self._viewer._dims_slider.value())
            fid_tr[:, 1] += (ny - 1) / 2
            fid_tr[:, 2] += (nx - 1) / 2
            fid_tr[:, 1:3] /= aligner._nbin
            self._viewer.set_points(fid_tr, size=10, out_of_slice=False)
            self._viewer.redraw()
        else:
            _LOGGER.debug("Fiducial file %s not found.", fid_path)


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

    def transform_image(self, img: np.ndarray, i: int) -> np.ndarray:
        ny, nx = img.shape
        t = np.array(
            [[1, 0, ny // self._nbin / 2], [0, 1, nx // self._nbin / 2], [0, 0, 1]]
        )
        a11, a12, a21, a22, dx, dy = self._components[i]
        mat = np.array(
            [[a22, a21, dy / self._nbin], [a12, a11, dx / self._nbin], [0, 0, 1]]
        )
        mat = t @ np.linalg.inv(mat) @ np.linalg.inv(t)
        imgb = _utils.bin_image(img, self._nbin)
        cval = np.mean(imgb[::50])
        return ndi.affine_transform(imgb.astype(np.float32), mat, order=1, cval=cval)

    def transform_points(self, fid: np.ndarray, i: int) -> np.ndarray:
        """Transform fiducial points for tilt index i."""
        a11, a12, a21, a22, dx, dy = self._components[i]
        mat = np.array([[a22, a12], [a21, a11]])
        fid = fid.copy()
        fid[:, 1:3] = (fid[:, 1:3] @ mat) + np.array([dy, dx])
        return fid


class QBatchruntomoLog(QtW.QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        font = QtGui.QFont(_utils.monospace_font_family(), 9)
        self.setFont(font)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )

    def minimumSizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(400, 300)
