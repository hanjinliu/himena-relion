from __future__ import annotations
from pathlib import Path
import logging
import numpy as np

import pandas as pd
from qtpy import QtWidgets as QtW, QtGui, QtCore
import scipy.ndimage as ndi
from himena_relion._image_readers._array import ArrayFilteredView
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    register_job,
    QMicrographListWidget,
)
from himena_relion import _job_dir, _utils
from himena_relion.relion5_tomo._tomo_utils import project_fiducials, read_xyz
from himena_relion.schemas._movie_tilts import TSModel, TSGroupModel

_LOGGER = logging.getLogger(__name__)


@register_job("relion.aligntiltseries", is_tomo=True)
class QAlignTiltSeriesViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._viewer = Q2DViewer(zlabel="Tilt index")
        self._viewer.setMinimumHeight(420)
        self._ts_list = QMicrographListWidget(["Tilt Series"])
        self._ts_list.current_changed.connect(self._ts_choice_changed)
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
        text = texts[0]  # tomo name
        xf = xf_file(job_dir, text)
        if not xf.exists():
            return

        # Don't use the tilt series inside IMOD project directories. They are redundant
        # and can be deleted by users after this job finished.
        in_tilt = job_dir.get_job_param("in_tiltseries")
        try:
            ts_group = TSGroupModel.validate_file(in_tilt)
            ts_file = ts_group.tomo_tilt_series_star_file[
                ts_group.tomo_name == text
            ].iloc[0]
            rln_dir = job_dir.relion_project_dir
            ts_paths = TSModel.validate_file(ts_file).ts_paths_sorted(rln_dir)
            ts_view = ArrayFilteredView.from_mrcs(ts_paths)
            nbin = max(round(16 / ts_view.get_scale()), 1)
            aligner = ImodImageAligner.from_xf(xf, nbin)
            self._viewer.set_array_view(ts_view.with_filter(aligner.transform_image))
            # TODO: not aligned well yet.
            # self._udpate_fiducials(text, aligner)
        except Exception:
            _LOGGER.error("Failed to load tilt series", exc_info=True)
            self._viewer.clear()

        # update batchruntomo log
        log_file = job_dir.path / "external" / text / "batchruntomo.log"
        if log_file.exists():
            self._batchruntomo_log.setPlainText(log_file.read_text())

    def _udpate_fiducials(self, text: str, aligner: ImodImageAligner):
        # if tracked fiducials are available, display them
        job_dir = self._job_dir
        if (fid_path := fid_file(job_dir, text)).exists() and (
            params := image_shape_params(job_dir, text)
        ):
            _LOGGER.debug("Fiducial file %s found. Load it.", fid_path)
            fid = read_xyz(fid_path)[:, ::-1]  # to zyx
            ny, nx = params

            fid_proj = project_fiducials(
                fid,
                np.array([0, ny - 1, nx - 1]) / 2,
                deg=np.loadtxt(fid_path.as_posix()[:-7] + "_fid.tlt"),
                xf=aligner._components,
                tilt_center=np.array([ny - 1, nx - 1]) / 2,
            )
            fid_proj[:, 1:] /= aligner._nbin
            fid_tr = aligner.transform_points(
                pd.DataFrame(fid_proj, columns=["z", "y", "x"]),
                (ny, nx),
            )
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
        mat = self.matrix(i, img.shape)
        imgb = _utils.bin_image(img, self._nbin)
        cval = np.mean(imgb[::50])
        out = ndi.affine_transform(
            imgb.astype(np.float32, copy=False), mat, order=1, cval=cval
        )
        return out

    def transform_points(
        self,
        fid: pd.DataFrame,
        shape: tuple[int, int],
    ) -> np.ndarray:
        """Transform fiducial points for tilt index i."""
        # fid is zyx
        fid_out = fid.to_numpy(np.float32, copy=True)
        for z, sub in fid.groupby("z"):
            mat = self.matrix(int(z), shape)
            fid_yx = sub[["y", "x"]].to_numpy(np.float32, copy=False)
            fid_yxz = np.hstack(
                [fid_yx, np.ones((fid_yx.shape[0], 1), dtype=np.float32)]
            )
            mask = fid_out[:, 0] == z
            fid_transformed = fid_yxz @ np.linalg.inv(mat.T)
            fid_out[mask, 1:3] = fid_transformed[:, 0:2]
        return fid_out

    def matrix(self, i: int, shape: tuple[int, int]) -> np.ndarray:
        """Get the transformation matrix for tilt index i."""
        ny, nx = shape
        t = np.array(
            [[1, 0, ny // self._nbin / 2], [0, 1, nx // self._nbin / 2], [0, 0, 1]]
        )
        a11, a12, a21, a22, dx, dy = self._components[i]
        mat = np.array(
            [[a22, a21, dy / self._nbin], [a12, a11, dx / self._nbin], [0, 0, 1]]
        )
        mat = t @ np.linalg.inv(mat) @ np.linalg.inv(t)
        return mat


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


def xf_file(jobdir: _job_dir.JobDirectory, tomoname: str) -> Path:
    """Return the path to the .xf file for a given tomogram name."""
    return jobdir.path / "external" / tomoname / f"{tomoname}.xf"


def fid_file(jobdir: _job_dir.JobDirectory, tomoname: str) -> Path:
    """Return the path to the .fid file for a given tomogram name."""
    # this is the mod file of tracked fiducials
    return jobdir.path / "external" / tomoname / f"{tomoname}fid.xyz"


def image_shape_params(
    jobdir: _job_dir.JobDirectory,
    tomoname: str,
) -> tuple[int, int] | None:
    """Try to get image shape from tilt.com and prenewst.com files."""
    path_tilt = jobdir.path / "external" / tomoname / "tilt.com"
    with path_tilt.open("r") as f:
        # FULLIMAGE 3838 3710
        for line in f:
            if line.startswith("FULLIMAGE "):
                nx, ny = map(int, line.split()[1:3])
    if ny > 0 and nx > 0:
        return (ny, nx)
    return None
