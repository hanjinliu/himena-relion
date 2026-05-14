from __future__ import annotations
from contextlib import suppress
from pathlib import Path
import logging
import numpy as np
from qtpy import QtWidgets as QtW, QtCore
from magicgui.widgets import FloatSlider
import mrcfile
from numpy.typing import NDArray
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    spacer_widget,
)
from himena.qt.magicgui import ToggleButtons
from himena_relion import _job_dir
from himena_relion._widgets._shared.resizer import QResizer

_LOGGER = logging.getLogger(__name__)


@register_job("relion.maskcreate")
class QMaskCreateViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        from himena_relion._widgets._vispy import MaskMesh

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
        self._layout.setSpacing(0)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(mask_slider)
        self._layout.addWidget(self._resizer)
        self._layout.addWidget(spacer_widget())
        self._mesh_layer = MaskMesh(parent=self._viewer._canvas._viewbox.scene)
        self._mask_level_slider.changed.connect(self._on_mask_level_changed)
        self._step_size.valueChanged.connect(self._on_mask_step_changed)
        self._mask_mode.changed.connect(self._on_mask_mode_changed)

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
        else:
            self._viewer.set_image(None, update_now=False)

        mask = mask_mrc(job_dir)
        if mask is not None:
            step_size = min(max(int(mask.shape[0] / 128), 1), 8)
            with QtCore.QSignalBlocker(self._step_size):
                self._step_size.setValue(step_size)
            self._mesh_layer.set_data(
                mask, level=self._mask_level_slider.value, step=step_size
            )
            self._mesh_layer.set_mode(self._mask_mode.value)
        self._viewer.auto_fit()

    def _on_mask_level_changed(self, value):
        self._mesh_layer.level = value
        self._viewer._canvas.update_canvas()

    def _on_mask_step_changed(self, value):
        self._mesh_layer.step_size = value
        self._viewer._canvas.update_canvas()

    def _on_mask_mode_changed(self, mode):
        self._mesh_layer.set_mode(mode)
        self._viewer._canvas.update_canvas()


def template_mrc(job_dir: _job_dir.JobDirectory) -> NDArray[np.floating] | None:
    """Return the template MRC file."""
    return _read_mrc(job_dir.get_job_param("fn_in"))


def mask_mrc(job_dir: _job_dir.JobDirectory) -> NDArray[np.floating] | None:
    """Return the mask MRC file."""
    return _read_mrc(job_dir.path / "mask.mrc")


def _read_mrc(path: Path) -> NDArray[np.floating] | None:
    with suppress(Exception):
        with mrcfile.open(path, mode="r") as mrc:
            return np.array(mrc.data)
