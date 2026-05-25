from __future__ import annotations
from functools import partial
from pathlib import Path
import logging
import subprocess
import numpy as np
import polars as pl

from contextlib import suppress
from qtpy import QtWidgets as QtW, QtGui, QtCore
import scipy.ndimage as ndi
from himena.consts import MonospaceFontFamily
from himena_relion._image_readers._array import ArrayFilteredView
from himena_relion._widgets._shared.resizer import QResizer
from himena_relion.relion5_tomo.widgets._tomogram import QTomogramViewer
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    register_job,
    QMicrographListWidget,
)
from himena_relion import _job_dir, _utils
from himena_relion.relion5_tomo._tomo_utils import project_fiducials
from himena_relion.schemas._movie_tilts import TSModel, TSGroupModel

_LOGGER = logging.getLogger(__name__)
_EXTERNAL = "external"


@register_job("relion.aligntiltseries", is_tomo=True)
def aligntilt_viewer(job_dir: _job_dir.JobDirectory):
    if job_dir.get_job_param("do_aretomo_reconstruct", default="No") == "Yes":
        return QAreTomo2TomogramViewer(job_dir)
    else:
        return QAlignTiltSeriesViewer(job_dir)


class QAlignTiltSeriesViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir

        job_params = job_dir.get_job_params_as_dict()
        self._is_imod_fid = job_params.get("do_imod_fiducials", "No") == "Yes"
        self._is_imod_patchtrack = job_params.get("do_imod_patchtrack", "No") == "Yes"
        self._is_aretomo2 = job_params.get("do_aretomo2", "No") == "Yes"

        self._viewer = Q2DViewer(zlabel="Tilt index")
        self._viewer.setMinimumHeight(420)
        self._resizer = QResizer(self._viewer)
        self._ts_list = QMicrographListWidget(["Tilt Series"])
        self._ts_list.current_changed.connect(self._ts_choice_changed)
        self._layout.setSpacing(2)
        self._layout.addWidget(self._ts_list)
        hlayout = QtW.QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(QtW.QLabel("<b>&#9679; Aligned tilt series</b>"))
        if self._is_imod_fid or self._is_imod_patchtrack:
            etomo_btn = QtW.QPushButton("Open in Etomo")
            etomo_btn.setToolTip("Open the etomo project for this tilt series")
            etomo_btn.setFixedWidth(104)
            etomo_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            etomo_btn.clicked.connect(self._open_in_etomo)
            hlayout.addWidget(etomo_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self._layout.addLayout(hlayout)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(self._resizer)

        self._align_log = QAlignJobLog()
        if self._is_imod_fid or self._is_imod_patchtrack:
            self._layout.addWidget(QtW.QLabel("<b>&#9679; Batchruntomo Log</b>"))
        else:
            self._layout.addWidget(QtW.QLabel("<b>&#9679; AreTomo2 Log</b>"))
        self._layout.addWidget(self._align_log)

    def on_job_updated(self, job_dir, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if self._is_imod_fid or self._is_imod_patchtrack:
            ok = fp.suffix == ".xf"
        elif self._is_aretomo2:
            ok = fp.name.endswith("_aligned.mrc")
        else:
            ok = False
        if fp.name.startswith("RELION_JOB_") or ok:
            self.initialize(self._job_dir)
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def initialize(self, job_dir):
        """Initialize the viewer with the job directory."""
        choices: list[str] = []
        for external_subdir in job_dir.path.joinpath(_EXTERNAL).glob("*"):
            if self._is_imod_fid or self._is_imod_patchtrack:
                # IMOD output alignment file
                filename = f"{external_subdir.name}.xf"
            elif self._is_aretomo2:
                # AreTomo2 output aligned tilt series
                filename = f"{external_subdir.name}_aligned.mrc"
            else:
                continue
            if external_subdir.joinpath(filename).exists():
                choices.append((external_subdir.name,))
        choices.sort(key=lambda x: x[0])
        self._ts_list.set_choices(choices)
        if len(choices) == 0:
            self._viewer.clear()

    def _ts_choice_changed(self, texts: tuple[str, ...]):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        text = texts[0]  # tomo name
        if self._is_imod_fid or self._is_imod_patchtrack:
            self._ts_choice_changed_imod(job_dir, text)
        elif self._is_aretomo2:
            self._ts_choice_changed_aretomo2(job_dir, text)

    def _ts_choice_changed_imod(self, job_dir: _job_dir.JobDirectory, text: str):
        xf = xf_file(job_dir, text)
        if not xf.exists():
            return

        # Don't use the tilt series inside IMOD project directories. They are redundant
        # and can be deleted by users after this job finished.
        in_tilt = job_dir.get_job_param("in_tiltseries")
        try:
            ts_group = TSGroupModel.validate_file(job_dir.resolve_path(in_tilt))
            ts_file = ts_group.tomo_tilt_series_star_file.filter(
                ts_group.tomo_name == text
            ).first()
            rln_dir = job_dir.relion_project_dir
            ts_model = TSModel.validate_file(ts_file)
            ts_paths = ts_model.ts_paths_sorted(rln_dir)
            _rot_90 = ts_model.need_rot90()

            ts_view = ArrayFilteredView.from_mrcs(ts_paths)
            nbin = max(round(16 / ts_view.get_scale()), 1)
            aligner = ImodImageAligner.from_xf(xf, nbin, rot90=_rot_90)
            self._viewer.set_array_view(ts_view.with_filter(aligner.transform_image))
            self._update_fiducials(text, aligner)
        except Exception:
            _LOGGER.error("Failed to load tilt series", exc_info=True)
            self._viewer.clear()

        # update batchruntomo log
        log_file = job_dir.path / _EXTERNAL / text / "batchruntomo.log"
        if log_file.exists():
            self._align_log.setPlainText(log_file.read_text())

    def _ts_choice_changed_aretomo2(self, job_dir: _job_dir.JobDirectory, text: str):
        aligned_file = job_dir.path / _EXTERNAL / text / f"{text}_aligned.mrc"
        if not aligned_file.exists():
            return
        try:
            ts_view = ArrayFilteredView.from_mrc(aligned_file)
            nbin = max(round(16 / ts_view.get_scale()), 1)
            filt = partial(bin_image, nbin=nbin)
            self._viewer.set_array_view(ts_view.with_filter(filt))
        except Exception:
            _LOGGER.error("Failed to load tilt series", exc_info=True)
            self._viewer.clear()

        log_file = job_dir.path / _EXTERNAL / text / f"{text}.log"
        if log_file.exists():
            self._align_log.setPlainText(log_file.read_text())

    def _update_fiducials(self, tomo_name: str, aligner: ImodImageAligner):
        # if tracked fiducials are available, display them
        job_dir = self._job_dir
        if (
            (params := image_shape_params(job_dir, tomo_name))
            and (path_3dmod := _3dmod_file(job_dir, tomo_name)).exists()
            and (path_tlt := _tlt_file(job_dir, tomo_name)).exists()
            and (preali_bin := _get_preali_bin(job_dir, tomo_name))
        ):
            fid = (
                _utils.read_mod(path_3dmod)
                .select("z", "y", "x")
                .to_numpy()
                .astype(np.float32)
                * preali_bin
            )
            ny, nx = params  # shape *after* transformation
            if aligner._rot90:
                ny0, nx0 = nx, ny  # before transformation
            else:
                ny0, nx0 = ny, nx
            fid_proj = project_fiducials(
                fid,
                np.array([0, ny - 1, nx - 1]) / 2,
                deg=np.loadtxt(path_tlt),
                xf=aligner._components,
                tilt_center=np.array([ny0 - 1, nx0 - 1]) / 2,
            )
            fid_proj[:, 1:] /= aligner._nbin
            fid_tr = aligner.transform_points(
                pl.DataFrame(fid_proj, schema=["z", "y", "x"]),
                (ny0, nx0),
            )
            self._viewer.set_points(fid_tr, size=10, out_of_slice=False)
            self._viewer.redraw()

    def _open_in_etomo(self):
        edf = edf_file(self._job_dir, self._ts_list.current_text())
        subprocess.Popen(
            ["etomo", edf.as_posix()],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


class ImodImageAligner:
    def __init__(self, components, nbin: int = 4, rot90: bool = False):
        self._components: np.ndarray = components
        self._nbin = nbin
        self._rot90 = rot90

    @classmethod
    def from_xf(cls, path, nbin: int = 4, rot90: bool = False) -> ImodImageAligner:
        """Create an ImodImageAligner from an IMOD .xf file."""
        components = np.loadtxt(path)
        return cls(components, nbin=nbin, rot90=rot90)

    @property
    def components(self) -> np.ndarray:
        """Return the alignment parameters as a numpy array."""
        return self._components

    def transform_image(self, img: np.ndarray, i: int) -> np.ndarray:
        mat = self.matrix(i, img.shape)
        imgb = _utils.bin_image(img, self._nbin)
        cval = np.mean(imgb[::50])
        if self._rot90:
            output_shape = (imgb.shape[1], imgb.shape[0])
        else:
            output_shape = imgb.shape
        out = ndi.affine_transform(
            imgb.astype(np.float32, copy=False),
            mat,
            order=1,
            cval=cval,
            output_shape=output_shape,
        )
        return out

    def transform_points(
        self,
        fid: pl.DataFrame,
        shape: tuple[int, int],
    ) -> np.ndarray:
        """Transform fiducial points for tilt index i."""
        # fid is zyx
        fid_out = fid.to_numpy().astype(np.float32)
        for (z,), sub in fid.group_by("z"):
            mat = self.matrix(int(z), shape)
            fid_yx = sub.select("y", "x").to_numpy().astype(np.float32)
            fid_yxz = np.hstack(
                [fid_yx, np.ones((fid_yx.shape[0], 1), dtype=np.float32)]
            )
            mask = fid_out[:, 0] == z
            fid_transformed = fid_yxz @ np.linalg.inv(mat.T)
            fid_out[mask, 1:3] = fid_transformed[:, 0:2]
        return fid_out

    def matrix(self, i: int, shape: tuple[int, int]) -> np.ndarray:
        """Get the transformation matrix for tilt index i."""
        ny, nx = shape  # shape *before* transformation
        nbin = self._nbin
        t = [[1, 0, ny // nbin / 2], [0, 1, nx // nbin / 2], [0, 0, 1]]
        if self._rot90:
            t_inv = [[1, 0, nx // nbin / 2], [0, 1, ny // nbin / 2], [0, 0, 1]]
        else:
            t_inv = t
        a11, a12, a21, a22, dx, dy = self.components[i]
        mat = [[a22, a21, dy / nbin], [a12, a11, dx / nbin], [0, 0, 1]]
        return t @ np.linalg.inv(mat) @ np.linalg.inv(t_inv)


class QAreTomo2TomogramViewer(QTomogramViewer):
    def _has_tomogram_splits(self, job_dir):
        return False

    def _get_binned_angpix(self, job_dir: _job_dir.JobDirectory) -> float:
        nbins = int(job_dir.get_job_param("aretomo_OutBin"))
        try:
            in_tilt = job_dir.get_job_param("in_tiltseries")
            ts_group = TSGroupModel.validate_file(in_tilt)
            return ts_group.original_pixel_size[0] * nbins
        except Exception:
            _LOGGER.warning(
                "Failed to get binned angpix for AreTomo2. Use default value.",
                exc_info=True,
            )
            return 3 * nbins


class QAlignJobLog(QtW.QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        font = QtGui.QFont(MonospaceFontFamily, 9)
        self.setFont(font)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )

    def minimumSizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(400, 300)


def xf_file(jobdir: _job_dir.JobDirectory, tomoname: str) -> Path:
    """Return the path to the .xf file for a given tomogram name."""
    return etomo_project_dir(jobdir, tomoname) / f"{tomoname}.xf"


def _3dmod_file(jobdir: _job_dir.JobDirectory, tomoname: str) -> Path:
    """Return the path to the .prexf file for a given tomogram name."""
    return etomo_project_dir(jobdir, tomoname) / f"{tomoname}.3dmod"


def _tlt_file(jobdir: _job_dir.JobDirectory, tomoname: str) -> Path:
    """Return the path to the .tlt file for a given tomogram name."""
    return etomo_project_dir(jobdir, tomoname) / f"{tomoname}.tlt"


def edf_file(jobdir: _job_dir.JobDirectory, tomoname: str) -> Path:
    """Return the path to the .edf file for a given tomogram name."""
    return etomo_project_dir(jobdir, tomoname) / f"{tomoname}.edf"


def etomo_project_dir(jobdir: _job_dir.JobDirectory, tomoname: str) -> Path:
    """Return the path to the etomo project directory for a given tomogram name."""
    return jobdir.path / _EXTERNAL / tomoname


def bin_image(img: np.ndarray, i: int, nbin: int) -> np.ndarray:
    if nbin > 1:
        img = _utils.bin_image(img, nbin)
    return img


def image_shape_params(
    jobdir: _job_dir.JobDirectory,
    tomoname: str,
) -> tuple[int, int] | None:
    """Try to get image shape from tilt.com and prenewst.com files."""
    path_tilt = etomo_project_dir(jobdir, tomoname) / "tilt.com"
    with suppress(Exception):
        with path_tilt.open("r") as f:
            # FULLIMAGE 3838 3710
            for line in f:
                if not line.startswith("#") and line.startswith("FULLIMAGE"):
                    nx, ny = map(int, line.split()[1:3])
        if ny > 0 and nx > 0:
            return (ny, nx)


def _get_preali_bin(jobdir: _job_dir.JobDirectory, tomoname: str) -> int | None:
    """Try to get pre-alignment binning from prenewst.com file."""
    path_align_com = etomo_project_dir(jobdir, tomoname) / "align.com"
    with suppress(Exception):
        with path_align_com.open("r") as f:
            # ImagesAreBinned 4
            for line in f:
                if not line.startswith("#") and line.startswith("ImagesAreBinned"):
                    return int(line.split()[1])
    return None


def _imod_output_align_file(subdir: Path) -> str:
    return f"{subdir.name}.xf"


def _aretomo2_output_align_file(subdir: Path) -> str:
    return f"{subdir.name}_aligned.mrc"
