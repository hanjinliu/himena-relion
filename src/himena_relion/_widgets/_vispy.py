from __future__ import annotations
import numpy as np
from numpy.typing import NDArray
from qtpy import QtWidgets as QtW

from vispy import scene
from vispy.scene import ViewBox
from vispy.app import use_app
from vispy.scene.visuals import (
    Image as VispyImage,
    Markers as VispyMarkers,
    Volume as VispyVolume,
)


class VispyViewerBase:
    def __init__(self):
        use_app("pyqt6")
        _scene = scene.SceneCanvas(keys="interactive")
        _scene.create_native()
        self._scene = _scene
        self._native_qt_widget = _scene.native

    @property
    def native(self) -> QtW.QWidget:
        return self._native_qt_widget


class Vispy2DViewer(VispyViewerBase):
    def __init__(self):
        super().__init__()
        viewbox = self._scene.central_widget.add_view(camera="panzoom")
        assert isinstance(viewbox, ViewBox)
        self._viewbox = viewbox

        # initialize camera
        self._viewbox.camera.aspect = 1.0
        self._viewbox.camera.flip = (False, True, False)

        # initialize image visual
        self._image = VispyImage(cmap="gray", parent=self._viewbox.scene)
        self._image.set_data(np.zeros((1, 1), dtype=np.float32))
        self._image.visible = False
        self._markers = VispyMarkers(
            pos=np.ones((1, 2), dtype=np.float32), scaling=True, face_color=np.zeros(4),
            edge_color="lime", size=10, parent=self._viewbox.scene
        )  # fmt: skip
        self._markers.update_gl_state(depth_test=False)
        self._markers.visible = False
        self._scene.events.mouse_double_click.connect(lambda event: self.auto_fit())

    @property
    def image(self) -> NDArray[np.float32]:
        return self._image._data

    @image.setter
    def image(self, img: NDArray[np.float32]):
        if img.size == 0:
            img = np.zeros((1, 1), dtype=np.float32)
            self._image.visible = False
        else:
            self._image.visible = True
        self._image.set_data(img)

    @property
    def markers_visual(self) -> VispyMarkers:
        return self._markers

    @property
    def contrast_limits(self) -> tuple[float, float]:
        return self._image.clim

    @contrast_limits.setter
    def contrast_limits(self, clim: tuple[float, float]):
        self._image.clim = clim

    def auto_fit(self):
        img = self.image
        self._viewbox.camera.set_range(
            x=(-0.5, img.shape[0] - 0.5), y=(-0.5, img.shape[1] - 0.5)
        )

    def set_camera_range(
        self, xrange: tuple[float, float], yrange: tuple[float, float]
    ):
        self._viewbox.camera.set_range(x=xrange, y=yrange)


class Vispy3DViewer(VispyViewerBase):
    def __init__(self):
        super().__init__()
        self._camera = scene.ArcballCamera(fov=0)
        grid = self._scene.central_widget.add_grid()
        viewbox = grid.add_view()
        assert isinstance(viewbox, ViewBox)
        viewbox.camera = self._camera
        self._viewbox = viewbox
        self._lims: tuple[float, float] = (0.0, 1.0)
        self._image_data = np.zeros((2, 2, 2), dtype=np.float32)
        self._volume_visual = VispyVolume(
            self._image_data,
            parent=self._viewbox.scene,
            threshold=1,
            cmap="grays",
            interpolation="linear",
            method="iso",
        )
        self._volume_visual.visible = False
        self._scene.events.mouse_double_click.connect(lambda event: self.auto_fit())

    @property
    def image(self) -> NDArray[np.float32]:
        return self._image_data

    @image.setter
    def image(self, img: NDArray[np.float32]):
        img = img.astype(np.float32, copy=False)
        if img.size == 0:
            img = np.zeros((2, 2, 2), dtype=np.float32)
            self._volume_visual.visible = False
        else:
            self._volume_visual.visible = True
        self._volume_visual.set_data(img, copy=False)
        self._image_data = img
        self._cache_lims(img)

    @property
    def image_visual(self) -> VispyVolume:
        return self._volume_visual

    @property
    def camera(self) -> scene.ArcballCamera:
        return self._camera

    @property
    def contrast_limits(self) -> tuple[float, float]:
        return self._volume_visual.clim

    @contrast_limits.setter
    def contrast_limits(self, clim: tuple[float, float]):
        self._volume_visual.clim = clim

    def set_iso_threshold(self, value):
        _min, _max = self._lims
        self._volume_visual.threshold = (value - _min) / (_max - _min)
        self._volume_visual.update()

    def auto_fit(self):
        img = self._image_data
        self._camera.center = np.array(img.shape) / 2
        self._camera.scale_factor = max(img.shape)
        self._camera.update()

    def _cache_lims(self, img):
        _min, _max = np.min(img), np.max(img)
        if _min == _max:
            _max = _min + 1e-6  # Avoid division by zero in thresholding
        self._lims = _min, _max
        self._volume_visual.clim = _min, _max
