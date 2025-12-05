from __future__ import annotations
from concurrent.futures import Future, ThreadPoolExecutor

import numpy as np
from qtpy import QtWidgets as QtW, QtCore
from superqt import ensure_main_thread
from vispy.app import use_app
from magicclass.ext.vispy import Vispy3DCanvas, VispyImageCanvas
from skimage.filters.thresholding import threshold_yen
from himena.qt._qlineedit import QIntLineEdit, QDoubleLineEdit
from himena_builtins.qt.widgets._shared import labeled
from himena_builtins.qt.widgets._image_components import QHistogramView
from himena_relion._image_readers import ArrayFilteredView
from himena_relion import _utils
# TODO: don't use magicclass


class Q2DViewer(QtW.QWidget):
    _executor = ThreadPoolExecutor(max_workers=2)

    def __init__(self, parent=None):
        super().__init__(parent)
        use_app("pyqt6")
        self._last_future: Future[tuple[np.ndarray, float, float]] | None = None
        self._last_clim: tuple[float, float] | None = None
        self._canvas = VispyImageCanvas()
        self._canvas.native.setFixedSize(340, 340)
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas.native)
        self._array_view = None
        self._dims_slider = QtW.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self._histogram_view = QHistogramView()
        self._histogram_view.clim_changed.connect(self._on_clim_changed)
        self._histogram_view.setFixedHeight(36)

        layout.addWidget(labeled("z", self._dims_slider))
        layout.addWidget(self._histogram_view)
        self._dims_slider.valueChanged.connect(self._on_slider_changed)

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
        self.redraw()

    def redraw(self):
        self._on_slider_changed(self._dims_slider.value(), force_sync=True)

    def _on_slider_changed(self, value: int, *, force_sync: bool = False):
        """Update the displayed slice based on the slider value."""
        if self._last_future:
            self._last_future.cancel()  # cancel last task
        if self._array_view is not None:
            if force_sync:
                slice_image, min_, max_ = self._get_image_slice(value)
                future = Future()
                future.set_result((slice_image, min_, max_))
                self._on_calc_slice_done(future)
            else:
                self._last_future = self._executor.submit(self._get_image_slice, value)
                self._last_future.add_done_callback(self._on_calc_slice_done)

            # TODO: don't update clim

    def _get_image_slice(self, slider_value: int):
        slice_image = np.asarray(self._array_view.get_slice(slider_value))
        if self._last_clim is None:
            min_ = slice_image.min()
            max_ = slice_image.max()
            self._last_clim = (min_, max_)
        else:
            min_, max_ = self._last_clim
        return slice_image, min_, max_

    @ensure_main_thread
    def _on_calc_slice_done(self, future: Future[tuple[np.ndarray, float, float]]):
        self._last_future = None
        if future.cancelled():
            return
        img, min_, max_ = future.result()
        self._canvas.image = img
        self._histogram_view.set_hist_for_array(img, (min_, max_))
        self._on_clim_changed((min_, max_))

    def _on_clim_changed(self, clim: tuple[float, float]):
        """Update the contrast limits based on the histogram view."""
        self._canvas.contrast_limits = clim
        self._last_clim = clim

    def auto_fit(self):
        """Automatically fit the camera to the image."""
        img = self._canvas.image
        self._canvas.xrange = (-0.5, img.shape[1])
        self._canvas.yrange = (-0.5, img.shape[0])

    def set_text_overlay(self, text: str, color: str = "white", size: int = 20):
        """Set a text overlay on the viewer."""
        # TODO


class Q3DViewer(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        use_app("pyqt6")
        self._canvas = Vispy3DCanvas()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas.native)
        self._image_layer = self._canvas.add_image(
            np.zeros((2, 2, 2)),
        )
        layout.addWidget(
            labeled("Threshold", self._image_layer.widgets.iso_threshold.native)
        )

    def set_image(self, image: np.ndarray | None):
        """Set the 3D image to be displayed."""
        if image is None:
            self._image_layer.data = np.zeros((2, 2, 2))
            self._image_layer.visible = False
        else:
            self._image_layer.data = image
            self._image_layer.contrast_limits = (np.min(image), np.max(image))
            self._image_layer.visible = True
        self._image_layer.rendering = "iso"

    def auto_threshold(self, thresh: float | None = None):
        """Automatically set the threshold based on the image data."""
        img = self._image_layer.data
        if self._image_layer.visible:
            if thresh is None:
                thresh = threshold_yen(img)
            self._image_layer.iso_threshold = thresh

    def auto_fit(self):
        """Automatically fit the camera to the image."""
        img = self._image_layer.data
        self._canvas.camera.center = np.array(img.shape) / 2
        self._canvas.camera.scale = max(img.shape)

    def set_text_overlay(self, text: str, color: str = "white", size: int = 20):
        """Set a text overlay on the viewer."""
        # TODO


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
