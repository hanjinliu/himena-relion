from __future__ import annotations

import numpy as np
from qtpy import QtWidgets as QtW, QtCore
from vispy.app import use_app
from magicclass.ext.vispy import Vispy3DCanvas, VispyImageCanvas
from skimage.filters.thresholding import threshold_yen
from himena_builtins.qt.widgets._shared import labeled
from himena_builtins.qt.widgets._image_components import QHistogramView
from himena_relion._image_readers import ArrayFilteredView
# TODO: don't use magicclass


class Q2DViewer(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        use_app("pyqt6")
        self._canvas = VispyImageCanvas()
        self._canvas.native.setFixedSize(340, 340)
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas.native)
        self._array_view = None
        self._dims_slider = QtW.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self._histogram_view = QHistogramView()
        self._histogram_view.clim_changed.connect(self._on_clim_changed)
        self._histogram_view.setFixedHeight(60)

        layout.addWidget(labeled("z", self._dims_slider))
        layout.addWidget(self._histogram_view)
        self._dims_slider.valueChanged.connect(self._on_slider_changed)

    def set_array_view(self, image: np.ndarray | ArrayFilteredView):
        """Set the 3D image to be displayed."""
        if isinstance(image, np.ndarray):
            self._array_view = ArrayFilteredView.from_array(image)
        else:
            self._array_view = image
        num_slices = self._array_view.num_slices()
        self._dims_slider.setRange(0, num_slices - 1)
        self._dims_slider.setValue(num_slices // 2)
        self._on_slider_changed(self._dims_slider.value())

    def _on_slider_changed(self, value: int):
        """Update the displayed slice based on the slider value."""
        if self._array_view is not None:
            # TODO: don't update clim
            slice_image = np.asarray(self._array_view.get_slice(value))
            self._canvas.image = slice_image
            min_ = slice_image.min()
            max_ = slice_image.max()
            self._histogram_view.set_hist_for_array(slice_image, (min_, max_))

    def _on_clim_changed(self, clim: tuple[float, float]):
        """Update the contrast limits based on the histogram view."""
        self._canvas.contrast_limits = clim

    def auto_fit(self):
        """Automatically fit the camera to the image."""
        img = self._canvas.image
        self._canvas.xrange = (-0.5, img.shape[1])
        self._canvas.yrange = (-0.5, img.shape[0])


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
