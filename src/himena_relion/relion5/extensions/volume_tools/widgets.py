from __future__ import annotations
from contextlib import suppress
from pathlib import Path
import logging
import numpy as np
import mrcfile
from magicgui.widgets import FloatSlider
from qtpy import QtWidgets as QtW, QtCore
from numpy.typing import NDArray
from himena.qt.magicgui import ToggleButtons
from himena.widgets import current_instance
from himena_relion._widgets._vispy import MaskMesh
from himena_relion._widgets import Q3DViewer, spacer_widget, QLowpassParamWidget
from himena_relion import _job_dir
from himena_relion._job_class import _JOB_DIR_ARGS_NAME
from himena_relion._utils import lowpass_filter
from himena_relion._widgets._shared.resizer import QResizer
from himena_relion.consts import FileNames, RelionJobState

_LOGGER = logging.getLogger(__name__)
_STATE_FILES = (
    FileNames.EXIT_SUCCESS,
    FileNames.EXIT_FAILURE,
    FileNames.EXIT_ABORTED,
    FileNames.ABORT_NOW,
)


class QMaskCreateViewer(QtW.QWidget):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._img_raw = None
        self._img_raw_scale = 1.0

        self._viewer = Q3DViewer()
        self._resizer = QResizer(self._viewer)
        self._mask_level_slider = FloatSlider(
            value=0.5, min=0.01, max=0.99, step=0.01, label="Mask Level"
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
        self._continue_btn = QtW.QPushButton("Continue drawing ...")
        self._continue_btn.setToolTip(
            "Continue this job to edit the mask again, starting from mask_base.mrc."
        )
        self._continue_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._continue_btn.clicked.connect(self._continue_clicked)
        self._continue_btn.setEnabled(False)
        self._job_dir = job_dir
        header = QtW.QWidget()
        header_layout = QtW.QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(self._message, stretch=1)
        header_layout.addWidget(
            self._continue_btn, alignment=QtCore.Qt.AlignmentFlag.AlignTop
        )
        self._lowpass_widget = QLowpassParamWidget()
        self._lowpass_widget.value_changed.connect(self._on_lowpass_changed)
        _layout = QtW.QVBoxLayout(self)
        _layout.setSpacing(0)
        _layout.addWidget(header)
        _layout.addWidget(self._lowpass_widget)
        _layout.addWidget(self._viewer)
        _layout.addWidget(mask_slider)
        _layout.addWidget(self._resizer)
        _layout.addWidget(spacer_widget())
        self._mesh_layer = MaskMesh(parent=self._viewer._canvas._viewbox.scene)
        self._mask_level_slider.changed.connect(self._on_mask_level_changed)
        self._step_size.valueChanged.connect(self._on_mask_step_changed)
        self._mask_mode.changed.connect(self._on_mask_mode_changed)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        name = Path(path).name
        if name == "mask.mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)
        elif name in _STATE_FILES:
            self._update_message(job_dir)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        template_path = job_dir.get_job_param("in_3dref")
        in_map = None
        with suppress(Exception):
            with mrcfile.open(template_path, mode="r") as mrc:
                in_map = mrc.data
                in_map_scale = float(mrc.voxel_size.x)
        if in_map is not None:
            self._img_raw = in_map
            self._img_raw_scale = in_map_scale
            self._viewer.set_image(self._get_image_filtered(), update_now=False)
            self._viewer.auto_threshold(update_now=False)
        else:
            self._img_raw = None
            self._img_raw_scale = 1.0
            self._viewer.set_image(None, update_now=False)

        mask = mask_mrc(job_dir)
        step_size = self._step_size.value()
        if mask is not None:
            self._mesh_layer.set_data(
                mask, level=self._mask_level_slider.value, step=step_size
            )
            self._mesh_layer.set_mode(self._mask_mode.value)
        self._update_message(job_dir)
        self._viewer.auto_fit()

    def _update_message(self, job_dir: _job_dir.JobDirectory):
        """Update the message and the button for the job state."""
        running = job_dir.state() is RelionJobState.RUNNING
        self._continue_btn.setEnabled(not running)
        has_mask = job_dir.path.joinpath("mask.mrc").exists()
        mask_base_path = _make_relative_path(job_dir.path, "mask_base.mrc")
        mask_path = _make_relative_path(job_dir.path, "mask.mrc")
        template_path = job_dir.get_job_param("in_3dref")
        if running and has_mask:
            # the job is continued
            self._message.setText(
                "Editing the mask. \n"
                f"Please save the updated binary mask {mask_base_path}\n"
                f"or blurred mask {mask_path}"
            )
        elif running:
            self._message.setText(
                "Mask file is not ready. \n"
                f"Please create and save a binary mask {mask_base_path}\n"
                f"or a blurred mask {mask_path}\n"
                f"using volume {template_path}"
            )
        elif has_mask:
            self._message.setText("mask.mrc")
        else:
            self._message.setText("Mask file not available.")

    def _continue_clicked(self):
        """Open the scheduler to continue this job."""
        from himena_relion.relion5.extensions.volume_tools.jobs import (
            ManualMaskCreationContinue,
        )

        ManualMaskCreationContinue._show_scheduler_widget_for_continue(
            current_instance(), {_JOB_DIR_ARGS_NAME: self._job_dir}
        )

    def _on_mask_level_changed(self, value):
        self._mesh_layer.level = value
        self._viewer._canvas.update_canvas()

    def _on_mask_step_changed(self, value):
        self._mesh_layer.step_size = value
        self._viewer._canvas.update_canvas()

    def _on_mask_mode_changed(self, mode):
        self._mesh_layer.set_mode(mode)
        self._viewer._canvas.update_canvas()

    def _on_lowpass_changed(self):
        self._viewer.set_image(self._get_image_filtered(), update_now=True)

    def _get_image_filtered(self):
        if (img := self._img_raw) is None:
            return None
        cutoff_a = self._lowpass_widget.value()
        cutoff_rel = self._img_raw_scale / cutoff_a
        img_filt = lowpass_filter(img, cutoff_rel)
        return img_filt


def template_mrc(job_dir: _job_dir.JobDirectory) -> NDArray[np.floating] | None:
    """Return the template MRC file."""
    template_path = job_dir.get_job_param("in_3dref")
    with suppress(Exception):
        with mrcfile.open(template_path, mode="r") as mrc:
            return mrc.data


def mask_mrc(job_dir: _job_dir.JobDirectory) -> NDArray[np.floating] | None:
    """Return the mask MRC file."""
    mask_path = job_dir.path / "mask.mrc"
    with suppress(Exception):
        with mrcfile.open(mask_path, mode="r") as mrc:
            return np.array(mrc.data)


def _make_relative_path(base: Path, filename: str):
    """`base` is the job directory path."""
    return f"{base.parent.name}/{base.name}/{filename}"
