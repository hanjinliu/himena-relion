from __future__ import annotations
from concurrent.futures import Future, ThreadPoolExecutor
from typing import NamedTuple
from himena import StandardType, WidgetDataModel
import numpy as np
from qtpy import QtWidgets as QtW, QtCore
from superqt import ensure_main_thread, QLabeledDoubleSlider
from himena.qt._qlineedit import QIntLineEdit, QDoubleLineEdit
from himena.plugins import validate_protocol
from himena_builtins.qt.widgets._shared import labeled
from himena_builtins.qt.widgets._image_components import QHistogramView

from himena_relion._image_readers import ArrayFilteredView
from himena_relion._widgets._spinbox import QIntWidget
from himena_relion._widgets._vispy import Vispy2DViewer, Vispy3DViewer
from himena_relion import _utils


class SliceResult(NamedTuple):
    image: np.ndarray
    clim: tuple[float, float]
    points: np.ndarray


class QViewer(QtW.QWidget):
    pass


class Q2DViewer(QViewer):
    _executor = ThreadPoolExecutor(max_workers=2)

    def __init__(self, zlabel: str = "z", parent=None):
        super().__init__(parent)
        self._last_future: Future[SliceResult] | None = None
        self._last_clim: tuple[float, float] | None = None
        self._canvas = Vispy2DViewer(self)
        self._canvas.native.setFixedHeight(340)
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas.native)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self._array_view = None
        self._points = np.empty((0, 3), dtype=np.float32)
        self._dims_slider = QtW.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self._dims_slider.setMaximum(0)
        self._dims_slider.setMinimumWidth(150)
        self._histogram_view = QHistogramView()
        self._histogram_view.clim_changed.connect(self._on_clim_changed)
        self._histogram_view.setFixedHeight(36)
        self._zpos_box = QIntWidget("", label_width=0)
        self._zpos_box.valueChanged.connect(self._on_zpos_box_changed)
        self._zpos_box.setFixedWidth(90)
        self._zpos_box.setMaximum(0)

        layout.addWidget(labeled(zlabel, self._dims_slider, self._zpos_box))
        layout.addWidget(self._histogram_view)
        self._dims_slider.valueChanged.connect(self._on_slider_changed)
        self._out_of_slice = True

    def clear(self):
        self._array_view = None
        self._points = np.empty((0, 3), dtype=np.float32)

    def set_array_view(
        self,
        image: np.ndarray | ArrayFilteredView,
        clim: tuple[float, float] | None = None,
    ):
        """Set the 3D image to be displayed."""
        if isinstance(image, np.ndarray):
            self._array_view = ArrayFilteredView.from_array(image)
        else:
            self._array_view = image
        self._last_clim = clim
        num_slices = self._array_view.num_slices()
        self._dims_slider.setRange(0, num_slices - 1)
        self._dims_slider.setValue(num_slices // 2)
        self._zpos_box.setRange(0, num_slices - 1)
        self.redraw()

    def set_points(self, points: np.ndarray, out_of_slice: bool = True):
        """Set the 3D points to be displayed."""
        self._points = points
        self._out_of_slice = out_of_slice

    def redraw(self):
        self._on_slider_changed(self._dims_slider.value(), force_sync=True)

    def _on_zpos_box_changed(self, value: int):
        """Update the slider when the z position box changes."""
        self._dims_slider.blockSignals(True)
        try:
            self._dims_slider.setValue(value)
        finally:
            self._dims_slider.blockSignals(False)

    def _on_slider_changed(self, value: int, *, force_sync: bool = False):
        """Update the displayed slice based on the slider value."""
        self._zpos_box.setValue(value)
        if self._last_future:
            self._last_future.cancel()  # cancel last task
        if self._array_view is not None:
            if force_sync:
                val = self._get_image_slice(value)
                future = Future()
                future.set_result(val)
                self._on_calc_slice_done(future)
            else:
                self._last_future = self._executor.submit(self._get_image_slice, value)
                self._last_future.add_done_callback(self._on_calc_slice_done)
        else:
            self._canvas.image = np.zeros((2, 2), dtype=np.float32)
            self._histogram_view.set_hist_for_array(
                np.zeros((2, 2), dtype=np.float32), (0.0, 1.0)
            )

    def _get_image_slice(self, slider_value: int) -> SliceResult:
        slice_image = np.asarray(self._array_view.get_slice(slider_value))
        if self._last_clim is None:
            min_ = slice_image.min()
            max_ = slice_image.max()
            self._last_clim = (min_, max_)
        else:
            min_, max_ = self._last_clim
        zs = self._points[:, 0]
        thick = 4 if self._out_of_slice else 0.1
        mask = (slider_value - thick / 2 <= zs) & (zs <= slider_value + thick / 2)
        points_in_slice = self._points[mask]
        return SliceResult(slice_image, (min_, max_), points_in_slice)

    @ensure_main_thread
    def _on_calc_slice_done(self, future: Future[SliceResult]):
        self._last_future = None
        if future.cancelled():
            return
        result = future.result()
        self._canvas.image = result.image
        self._histogram_view.set_hist_for_array(result.image, result.clim)
        self._on_clim_changed(result.clim)
        if result.points.shape[0] > 0:
            self._canvas.markers_visual.set_data(
                result.points[:, [2, 1]],
                face_color=np.zeros(4),
                edge_color="lime",
                size=10,
            )
            self._canvas.markers_visual.visible = True
        else:
            self._canvas.markers_visual.set_data(
                np.ones((1, 2), dtype=np.float32),
                face_color=np.zeros(4),
                edge_color=np.zeros(4),
                size=10,
            )
            self._canvas.markers_visual.visible = False

    def _on_clim_changed(self, clim: tuple[float, float]):
        """Update the contrast limits based on the histogram view."""
        self._canvas.contrast_limits = clim
        self._last_clim = clim

    def auto_fit(self):
        """Automatically fit the camera to the image."""
        self._canvas.auto_fit()

    def set_text_overlay(self, text: str, color: str = "white", size: int = 20):
        """Set a text overlay on the viewer."""
        # TODO


class Q3DViewer(QViewer):
    __himena_widget_id__ = "himena-relion:Q3DViewer"
    __himena_display_name__ = "3D volume viewer"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._canvas = Vispy3DViewer(self)
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self._iso_slider = QLabeledDoubleSlider(QtCore.Qt.Orientation.Horizontal)
        self._iso_slider.valueChanged.connect(self._on_iso_changed)
        self._has_image = False

        layout.addWidget(self._canvas.native)
        layout.addWidget(labeled("Threshold", self._iso_slider))

    def set_image(self, image: np.ndarray | None):
        """Set the 3D image to be displayed."""
        if image is None:
            self._canvas.image = np.zeros((2, 2, 2))
            self._canvas.image_visual.visible = False
            self._has_image = False
        else:
            self._canvas.image = image
            self._canvas.image_visual.visible = True
            self._has_image = True
        self._canvas.set_iso_threshold(self._iso_slider.value())

    def auto_threshold(self, thresh: float | None = None):
        """Automatically set the threshold based on the image data."""
        img = self._canvas.image
        if self._canvas.image_visual.visible:
            if thresh is None:
                thresh = _utils.threshold_yen(img)
            self._iso_slider.setValue(thresh)
            self._iso_slider.setRange(*self._canvas._lims)

    def auto_fit(self):
        """Automatically fit the camera to the image."""
        img = self._canvas.image
        self._canvas.camera.center = np.array(img.shape) / 2
        self._canvas.camera.scale_factor = max(img.shape)
        self._canvas.camera.update()

    def set_text_overlay(self, text: str, color: str = "white", size: int = 20):
        """Set a text overlay on the viewer."""
        # TODO

    def _on_iso_changed(self, value: float):
        self._canvas.set_iso_threshold(value)

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        arr = np.asarray(model.value, dtype=np.float32)
        if arr.ndim != 3:
            raise ValueError("Input array must be 3D.")
        had_image = self._has_image
        self.set_image(arr)
        if not had_image:
            self.auto_threshold()
            self.auto_fit()

    @validate_protocol
    def model_type(self) -> str:
        return StandardType.IMAGE

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._canvas.image,
            type=StandardType.IMAGE,
        )

    @validate_protocol
    def size_hint(self):
        return 330, 350


class Q2DFilterWidget(QtW.QWidget):
    value_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self._bin_factor = QIntLineEdit("4")
        self._bin_factor.setFixedWidth(60)
        self._bin_factor.setMinimum(1)
        self._bin_factor.setMaximum(20)
        self._lowpass_cutoff = QDoubleLineEdit("10")
        self._lowpass_cutoff.setMinimum(0.0)
        self._lowpass_cutoff.setMaximum(200.0)
        self._lowpass_cutoff.setFixedWidth(80)
        layout.addWidget(labeled("Binning factor:", self._bin_factor))
        layout.addWidget(labeled("Lowpass cutoff (Å):", self._lowpass_cutoff))
        self._image_scale = 1.0
        self._bin_factor.textChanged.connect(self.value_changed)
        self._lowpass_cutoff.textChanged.connect(self.value_changed)

    def set_image_scale(self, scale: float):
        """Set the image scale in Å/pixel."""
        self._image_scale = scale

    def bin_factor(self) -> int:
        """Get the binning factor from the input."""
        return int(self._bin_factor.text())

    def lowpass_cutoff(self) -> float:
        """Get the lowpass cutoff frequency from the input."""
        return float(self._lowpass_cutoff.text())

    def apply(self, img: np.ndarray, index=None) -> np.ndarray:
        """Apply the binning and lowpass filter to the input image."""
        # Binning
        factor = self.bin_factor()
        cutoff = self.lowpass_cutoff()
        if factor > 1:
            img = _utils.bin_image(img, factor)
        if cutoff > 0.0:
            cutoff_rel = self._image_scale / cutoff
            img = _utils.lowpass_filter(img, cutoff_rel)

        return img
