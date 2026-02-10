from __future__ import annotations
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
from himena_relion.schemas import OptimisationSetModel

_LOGGER = logging.getLogger(__name__)


@register_job("relion.reconstructparticletomo", is_tomo=True)
class QReconstructViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._lowpass_widget = QLowpassParamWidget()
        self._lowpass_widget.value_changed.connect(self._on_lowpass_changed)
        self._viewer = Q3DViewer()
        self._viewer.setMaximumWidth(400)
        self._num_particles_label = QNumParticlesLabel()
        self._num_particles_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._num_particles_label.setMaximumWidth(self._viewer.maximumWidth())
        self._layout.addWidget(self._lowpass_widget)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(self._num_particles_label)
        self._img_raw = None
        self._img_raw_scale = 1.0

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        merged_mrc_path = merged_mrc(job_dir)
        if not merged_mrc_path.exists():
            return
        with mrcfile.open(merged_mrc_path, permissive=True) as mrc:
            self._img_raw = np.array(mrc.data)
            self._img_raw_scale = float(mrc.voxel_size.x)
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
