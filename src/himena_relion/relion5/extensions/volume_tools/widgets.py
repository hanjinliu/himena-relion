from __future__ import annotations
from pathlib import Path
import logging
import numpy as np
import mrcfile
from magicgui.widgets import FloatSlider
from qtpy import QtWidgets as QtW, QtCore
from numpy.typing import NDArray
from himena.qt.magicgui import ToggleButtons
from himena_relion._widgets._vispy import MaskMesh
from himena_relion._widgets import Q3DViewer
from himena_relion import _job_dir
from himena_relion._widgets._shared.resizer import QResizer
from himena_relion.consts import RelionJobState

_LOGGER = logging.getLogger(__name__)


class QMaskCreateViewer(QtW.QWidget):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._viewer = Q3DViewer()
        self._resizer = QResizer(self._viewer)
        self._mask_level_slider = FloatSlider(
            value=0.5, min=0.01, max=1.0, step=0.01, label="Mask Level"
        )
        self._step_size = QtW.QSpinBox()
        self._step_size.setPrefix("step ")
        self._step_size.setRange(1, 8)
        self._step_size.setFixedWidth(80)
        self._mask_mode = ToggleButtons(
            choices=[("Surf", "surface"), ("Wire", "wireframe")],
            label="Mask Render Mode",
        )
        mask_slider = QtW.QWidget()
        hlayout = QtW.QHBoxLayout(mask_slider)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(QtW.QLabel("Mask:"))
        hlayout.addWidget(self._mask_mode.native)
        hlayout.addWidget(self._step_size)
        hlayout.addWidget(self._mask_level_slider.native)
        mask_slider.setMaximumWidth(400)
        self._message = QtW.QLabel("")
        self._message.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        _layout = QtW.QVBoxLayout(self)
        _layout.setSpacing(0)
        _layout.addWidget(self._message)
        _layout.addWidget(self._viewer)
        _layout.addWidget(self._resizer)
        self._mesh_layer = MaskMesh(parent=self._viewer._canvas._viewbox.scene)
        self._mask_level_slider.changed.connect(self._on_mask_level_changed)
        self._step_size.valueChanged.connect(self._on_mask_step_changed)
        self._mask_mode.changed.connect(self._on_mask_mode_changed)
        self.initialize(job_dir)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).name == "mask.mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        in_map = template_mrc(job_dir)
        if in_map is not None:
            self._viewer.set_image(in_map, update_now=False)
            self._viewer.auto_threshold(update_now=False)

        mask = mask_mrc(job_dir)
        if mask is not None:
            self._message.setText("mask.mrc")
            self._mesh_layer.set_data(mask, level=0.4)
        elif job_dir.state() is RelionJobState.RUNNING:
            mask_base_path = job_dir.path / "mask_base.mrc"
            mask_path = job_dir.path / "mask.mrc"
            self._message.setText(
                "Mask file is not ready. \n"
                f"Please create and save a binary mask {mask_base_path}\n"
                f"or a blurred mask {mask_path}."
            )
        else:
            self._message.setText("Mask file not available.")
        self._viewer.auto_fit()

    def _on_mask_level_changed(self, value):
        self._mesh_layer.level = value

    def _on_mask_step_changed(self, value):
        self._mesh_layer.step_size = value

    def _on_mask_mode_changed(self, mode):
        self._mesh_layer.set_mode(mode)


def template_mrc(job_dir: _job_dir.JobDirectory) -> NDArray[np.floating] | None:
    """Return the template MRC file."""
    template_path = job_dir.get_job_param("fn_in")
    try:
        with mrcfile.open(template_path, mode="r") as mrc:
            return mrc.data
    except Exception:
        return None


def mask_mrc(job_dir: _job_dir.JobDirectory) -> NDArray[np.floating] | None:
    """Return the mask MRC file."""
    mask_path = job_dir.path / "mask.mrc"
    try:
        with mrcfile.open(mask_path, mode="r") as mrc:
            return np.array(mrc.data)
    except Exception:
        return None
