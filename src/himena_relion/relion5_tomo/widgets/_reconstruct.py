from __future__ import annotations
from contextlib import suppress
from pathlib import Path
import logging

import mrcfile
import numpy as np
from qtpy import QtWidgets as QtW, QtCore
from starfile_rs import read_star
from superqt import QToggleSwitch
from himena.qt._qlineedit import QDoubleLineEdit
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    QNumParticlesLabel,
)
from himena_relion import _job_dir
from himena_relion._utils import lowpass_filter
from himena_relion.schemas import OptimisationSetModel, TomogramsGroupModel

_LOGGER = logging.getLogger(__name__)


@register_job("relion.reconstructparticletomo", is_tomo=True)
class QReconstructViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._file_name_label = QtW.QLabel()
        self._lowpass_widget = QLowpassParamWidget()
        self._lowpass_widget.value_changed.connect(self._on_lowpass_changed)
        self._viewer = Q3DViewer()
        self._viewer.setMaximumWidth(400)
        self._num_particles_label = QNumParticlesLabel()
        self._num_particles_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._num_particles_label.setMaximumWidth(self._viewer.maximumWidth())

        self._layout.addWidget(self._file_name_label)
        self._layout.addWidget(self._lowpass_widget)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(self._num_particles_label)

        self._img_raw = None
        self._img_raw_scale = 1.0

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        # NOTE: sometimes half1 will not be generated.
        if (
            fp.name.startswith("RELION_JOB_")
            or fp.name == "merged.mrc"
            or fp.name.endswith("_data_half0.mrc")
        ):
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        merged_mrc_path = merged_mrc(job_dir)
        if not merged_mrc_path.exists():
            return self._open_intermediate_result(job_dir)
        with mrcfile.open(merged_mrc_path, permissive=True) as mrc:
            self._img_raw = np.array(mrc.data)
            self._img_raw_scale = float(mrc.voxel_size.x)

        self._file_name_label.setText("merged.mrc")
        self._viewer.set_image(self._get_image_filtered(), update_now=False)
        self._viewer.auto_threshold(update_now=False)
        self._viewer.auto_fit()

        # get the number of particles
        try:
            params = job_dir.get_job_params_as_dict()
            if opt_path := params.get("in_optimisation", None):
                opt_path = job_dir.relion_project_dir / opt_path
                opt_model = OptimisationSetModel.validate_file(opt_path)
                particles_path = opt_model.particles_star
            elif ptcl := params.get("in_particles", None):
                particles_path = job_dir.resolve_path(ptcl)
            else:
                return
            if not particles_path.exists():
                particles_path = job_dir.relion_project_dir / particles_path
            star = read_star(particles_path)
            if "particles" in star:
                n_particles = star["particles"].trust_loop().shape[0]
            elif len(star) == 1:
                n_particles = star.first().trust_loop().shape[0]
            else:
                n_particles = -1
        except Exception:
            n_particles = -1
            _LOGGER.warning(
                "Failed to read particles star file to get number of particles",
                exc_info=True,
            )
        self._num_particles_label.set_number(n_particles)

    def _open_intermediate_result(self, job_dir: _job_dir.JobDirectory):
        temp_dir = job_dir.path / "temp"
        if not temp_dir.exists():
            self._img_raw = None
            self._viewer.set_image(None, update_now=False)
            return
        image_data: list[np.ndarray] = []
        ith_tomo = "0"
        for impath in temp_dir.glob("sum_*_data_half?.mrc"):
            with mrcfile.open(impath, mode="r") as mrc:
                image_data.append(mrc.data)
            ith_tomo = impath.stem.split("_")[1]
        if len(image_data) == 0:
            return
        # Every sum_X_data_halfX.mrc is a (2N, N, N/2) float32 image for a (N, N, N)
        # reconstruction. The first N planes are the real part and the next N planes are
        # the imaginary part of the Fourier transform.
        merged_c = sum(image_data)
        nz = merged_c.shape[0]
        merged_ft = merged_c[: nz // 2] + merged_c[nz // 2 :] * 1j
        self._img_raw = np.fft.ifftshift(np.fft.irfftn(merged_ft))

        # Try to get the pixel size. Pixel size is not set in the sum_X_data_halfX.mrc
        # files, so we need to retrieve it from the input parameters.
        params = job_dir.get_job_params_as_dict()

        tomo_star = None
        with suppress(Exception):
            binning = int(params["binning"])
            if in_opt := params["in_optimisation"]:
                tomo_star = OptimisationSetModel.validate_file(
                    job_dir.resolve_path(in_opt)
                ).tomogram_star
            elif in_tomo := params["in_tomograms"]:
                tomo_star = job_dir.resolve_path(in_tomo)

        if tomo_star:
            tomo_model = TomogramsGroupModel.validate_file(tomo_star)
            self._img_raw_scale = tomo_model.original_pixel_size.mean() * binning
        else:
            self._img_raw_scale = 0.3 * binning  # fallback

        self._file_name_label.setText(
            f"Intermediate reconstruction ({int(ith_tomo) + 1})"
        )
        self._viewer.set_image(self._get_image_filtered(), update_now=False)
        self._viewer.auto_threshold(update_now=False)
        self._viewer.auto_fit()

    def _on_lowpass_changed(self):
        self._viewer.set_image(self._get_image_filtered(), update_now=True)

    def _get_image_filtered(self):
        if (img := self._img_raw) is None:
            return None
        cutoff_a = self._lowpass_widget.value()
        cutoff_rel = self._img_raw_scale / cutoff_a
        img_filt = lowpass_filter(img, cutoff_rel)
        return img_filt


def merged_mrc(job_dir: _job_dir.JobDirectory) -> Path:
    """Return the path to the merged MRC file if exists."""
    return job_dir.path / "merged.mrc"


class QLowpassParamWidget(QtW.QWidget):
    value_changed = QtCore.Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QtW.QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self._do_lowpass_switch = QToggleSwitch("Apply lowpass filter")
        self._do_lowpass_switch.setChecked(False)
        self._cutoff = QDoubleLineEdit()
        self._cutoff.setText("8.0")
        self._cutoff.setMinimum(0.1)
        self._cutoff.setFixedWidth(50)
        self._layout.addWidget(self._do_lowpass_switch)
        self._layout.addSpacing(3)
        _cutoff_label = QtW.QLabel("Cutoff:")
        _cutoff_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self._layout.addWidget(_cutoff_label)
        self._layout.addWidget(self._cutoff)
        self._layout.addWidget(QtW.QLabel("A"))
        self._cutoff.setEnabled(False)
        self._do_lowpass_switch.toggled.connect(self._switch_toggled)
        self._cutoff.valueChanged.connect(self._emit_value)
        self.setMaximumWidth(360)

    def _switch_toggled(self, checked: bool):
        self._cutoff.setEnabled(checked)
        self._emit_value()

    def value(self) -> float:
        if self._do_lowpass_switch.isChecked():
            try:
                cutoff = float(self._cutoff.text())
                return cutoff
            except ValueError:
                return -1.0
        else:
            return -1.0

    def _emit_value(self):
        cutoff = self.value()
        self.value_changed.emit(cutoff)
