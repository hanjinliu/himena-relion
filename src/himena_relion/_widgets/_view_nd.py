from __future__ import annotations

import numpy as np
from qtpy import QtWidgets as QtW, QtCore
from vispy.app import use_app
from magicclass.ext.vispy import Vispy3DCanvas, VispyImageCanvas
from skimage.filters.thresholding import threshold_yen


class Q2DViewer(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        use_app("pyqt6")
        self._canvas = VispyImageCanvas()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas.native)
        self._tomogram = None
        self._dims_slider = QtW.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        layout.addWidget(self._dims_slider)
        self._dims_slider.valueChanged.connect(self._on_slider_changed)

    def set_image(self, image: np.ndarray):
        """Set the 3D image to be displayed."""
        self._tomogram = image
        self._dims_slider.setRange(0, image.shape[0] - 1)
        self._dims_slider.setValue(image.shape[0] // 2)
        self._on_slider_changed(self._dims_slider.value())

    def _on_slider_changed(self, value: int):
        """Update the displayed slice based on the slider value."""
        if self._tomogram is not None:
            slice_image = self._tomogram[value, :, :]
            self._canvas.image = np.asarray(slice_image)


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
        layout.addWidget(self._image_layer.widgets.iso_threshold.native)

    def set_image(self, image: np.ndarray):
        """Set the 3D image to be displayed."""
        self._image_layer.data = image
        self._image_layer.contrast_limits = (np.min(image), np.max(image))
        self._image_layer.rendering = "iso"
        self._image_layer.iso_threshold = threshold_yen(image)
        self._canvas.camera.center = np.array(image.shape) / 2
        self._canvas.camera.scale = max(image.shape)

    def set_text_overlay(self, text: str, color: str = "white", size: int = 20):
        """Set a text overlay on the viewer."""
        # TODO
