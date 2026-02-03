from __future__ import annotations
from functools import lru_cache
from typing import Literal, TYPE_CHECKING
import numpy as np
from numpy.typing import NDArray
from psygnal import Signal

from vispy import scene, use
from vispy.scene import ViewBox
from vispy.scene.visuals import (
    Image as VispyImage,
    Markers as VispyMarkers,
    Volume as VispyVolume,
    Arrow as VispyArrow,
)
from vispy.visuals.transforms import STTransform
from himena_relion._image_readers import ArrayFilteredView
from himena_relion._widgets._vispy._viewbox import (
    QOffScreenViewBox,
    QNativeViewBox,
    ArcballCamera,
)
from himena_relion._widgets._vispy.motion import MotionPath
from himena_relion._impl_objects import TubeObject

if TYPE_CHECKING:
    from vispy.app import MouseEvent


@lru_cache(maxsize=1)
def is_egl_available() -> bool:
    try:
        use("egl")
        return True
    except Exception:
        return False


class _Vispy2DBase:
    def __init__(self):
        _scene = self.make_scene()
        self._scene = _scene
        self._native_qt_widget = _scene.native
        viewbox = self._scene.central_widget.add_view(camera="panzoom")
        assert isinstance(viewbox, ViewBox)
        self._viewbox = viewbox

        # initialize camera
        self._viewbox.camera.aspect = 1.0
        self._viewbox.camera.flip = (False, True, False)

        # initialize image visual
        self._image = VispyImage(cmap="gray", parent=self._viewbox.scene)
        self._image.set_gl_state(preset="opaque")
        self._image.set_data(np.zeros((1, 1), dtype=np.float32))
        self._image.visible = False
        self._markers = VispyMarkers(
            pos=np.ones((1, 2), dtype=np.float32), scaling=True, face_color=np.zeros(4),
            edge_color="lime", size=10, parent=self._viewbox.scene,
        )  # fmt: skip
        self._markers.update_gl_state(depth_test=False)
        self._markers.visible = False
        self._scene.events.mouse_double_click.connect(lambda event: self.auto_fit())

    def make_scene(self) -> scene.SceneCanvas:
        raise NotImplementedError

    @property
    def camera(self) -> scene.PanZoomCamera:
        return self._viewbox.camera

    @property
    def image(self) -> NDArray[np.float32]:
        return self._image._data

    @image.setter
    def image(self, img: NDArray[np.float32] | None):
        if img is None or img.size == 0:
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


class _Vispy3DBase:
    _volume_visual: VispyVolume

    def __init__(self):
        self._scene = self.make_scene()
        self._camera = ArcballCamera(fov=0)
        viewbox = self._scene.central_widget.add_view()
        assert isinstance(viewbox, ViewBox)
        viewbox.camera = self._camera
        self._viewbox = viewbox
        self._lims: tuple[float, float] = (0.0, 1.0)
        self._image_data = np.zeros((2, 2, 2), dtype=np.float32)

    def make_scene(self) -> scene.SceneCanvas:
        raise NotImplementedError

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

    def _cache_lims(self, img):
        _min, _max = np.min(img), np.max(img)
        if _min == _max:
            _max = _min + 1e-6  # Avoid division by zero in thresholding
        self._lims = _min, _max
        self._volume_visual.clim = _min, _max

    @property
    def camera(self) -> ArcballCamera:
        return self._camera

    @property
    def contrast_limits(self) -> tuple[float, float]:
        """Contrast limits (min, max) for volume rendering."""
        return self._volume_visual.clim

    @contrast_limits.setter
    def contrast_limits(self, clim: tuple[float, float]):
        self._volume_visual.clim = clim

    def auto_fit(self):
        img = self._image_data
        self._camera.center = np.array(img.shape) / 2
        self._camera.scale_factor = max(img.shape)
        self._camera.update()


class _Vispy3DDensityBase(_Vispy3DBase):
    def __init__(self):
        super().__init__()
        self._volume_visual = VispyVolume(
            self._image_data,
            parent=self._viewbox.scene,
            threshold=1,
            cmap="grays",
            interpolation="linear",
            method="iso",
        )
        self._volume_visual.set_gl_state(preset="opaque")
        self._volume_visual.visible = False

        self._scene.events.mouse_double_click.connect(lambda _: self.auto_fit())
        self._arrow_visual = VispyArrow(
            connect="segments",
            width=2.0,
            antialias=False,
            parent=self._viewbox.scene,
        )
        self._arrow_visual.set_gl_state(preset="translucent")

    @property
    def arrow_visual(self) -> VispyArrow:
        return self._arrow_visual

    def set_rendering_mode(self, mode: str):
        if mode == "Surface":
            self._volume_visual.method = "iso"
        elif mode == "Maximum":
            self._volume_visual.method = "mip"
        elif mode == "Average":
            self._volume_visual.method = "average"
        else:
            raise ValueError(f"Unknown rendering mode: {mode}")

    def set_iso_threshold(self, value):
        _min, _max = self._lims
        self._volume_visual.threshold = (value - _min) / (_max - _min)
        self._volume_visual.update()

    def set_arrows(self, tubes: list[TubeObject]):
        colors = []
        arrow_colors = []
        arrows = []
        pos = []
        for tube in tubes:
            arrows.append(np.concatenate([tube.start[::-1], tube.end[::-1]]))
            arrow_colors.append(tube.color)
            pos.append(tube.start[::-1])
            pos.append(tube.end[::-1])
            colors.append(tube.color)
            colors.append(tube.color)
        if colors:
            colors = np.stack(colors, axis=0)
            arrow_colors = np.stack(arrow_colors, axis=0)
            arrows = np.stack(arrows, axis=0)
            pos = np.stack(pos, axis=0)
        else:
            colors = np.zeros((0, 4), dtype=np.float32)
            arrow_colors = np.zeros((0, 4), dtype=np.float32)
            arrows = np.zeros((0, 6), dtype=np.float32)
            pos = np.zeros((0, 3), dtype=np.float32)
        self._arrow_visual.set_data(
            pos=pos,
            color=colors,
            width=2.0,
            connect="segments",
            arrows=arrows,
        )
        self._arrow_visual.arrow_color = arrow_colors


class _Vispy3DTomogramBase(_Vispy3DBase):
    plane_position_changed = Signal(int)

    def __init__(self, raycasting_mode: Literal["volume", "plane"] = "plane"):
        super().__init__()
        self._volume_visual = VispyVolume(
            np.zeros((2, 2, 2), dtype=np.float32),
            parent=self._viewbox.scene,
            threshold=1,
            cmap="grays",
            interpolation="linear",
            method="minip",
        )
        self._volume_visual.set_gl_state(preset="opaque")
        self._volume_visual.visible = False

        self._scene.events.mouse_move.connect(self._on_mouse_move)
        self._markers = VispyMarkers(
            pos=np.ones((1, 3), dtype=np.float32), scaling=True, face_color=np.zeros(4),
            edge_color="lime", size=10, parent=self._viewbox.scene
        )  # fmt: skip
        self._motion_visual = MotionPath(parent=self._viewbox.scene)
        self._markers.visible = False
        self._markers.set_gl_state("opaque")
        self._volume_visual.raycasting_mode = raycasting_mode
        self._volume_visual.relative_step_size = 0.8
        self._plane_position: int = 0
        self._array_view = None
        self._current_image_slice: NDArray[np.float32] | None = None
        self._array_view_nz = 1
        self.camera.rotation = self.camera.rotation.from_rotvec([-0.37, 1.06, -0.132])

    def set_array_view(
        self,
        array_view: ArrayFilteredView,
        clim: tuple[float, float] | None = None,
    ):
        self._array_view = array_view
        nz = self._array_view_nz = array_view.num_slices()
        self.set_plane_position((nz - 1) // 2)
        self._volume_visual.visible = True

        if clim is None:
            if (arr := self._current_image_slice) is not None:
                clim = (float(np.min(arr)), float(np.max(arr)))
            else:
                clim = (-1.0, 1.0)
        self.contrast_limits = clim

    @property
    def markers_visual(self) -> VispyMarkers:
        return self._markers

    @property
    def motion_visual(self):
        return self._motion_visual

    def set_plane_position(self, zpos: int):
        zpos = max(0, min(self._array_view_nz - 1, zpos))
        arr_2d = self._array_view.get_slice(zpos)
        self._current_image_slice = arr_2d
        self._volume_visual.set_data(arr_2d[np.newaxis], copy=False)
        self._volume_visual.transform = STTransform(translate=(0, 0, zpos))
        self._volume_visual.plane_position = [0, 0, zpos]
        self._plane_position = zpos
        self.plane_position_changed.emit(zpos)
        self._volume_visual.update()

    def _on_mouse_move(self, event: MouseEvent):
        if event.button == 1 and "control" in event.modifiers:
            if (events := event.drag_events()) and len(events) >= 2:
                prev = events[-2]
                new = events[-1]
                xy = new.pos - prev.pos
                speed = 1
                zpos = int(self._plane_position - xy[1] * speed)
                self.set_plane_position(zpos)

    def auto_fit(self):
        if self._array_view is None:
            return
        nz = self._array_view_nz
        ny, nx = self._array_view.get_shape()
        img_shape = (nx, ny, nz)
        self._camera.center = np.array(img_shape) / 2
        self._camera.scale_factor = max(img_shape)
        self._camera.update()


##########################################################
###   Concrete viewer classes
##########################################################


class VispyOffScreen2DViewer(QOffScreenViewBox, _Vispy2DBase):
    def __init__(self, parent):
        super().__init__(parent)
        _Vispy2DBase.__init__(self)


class VispyNative2DViewer(QNativeViewBox, _Vispy2DBase):
    def __init__(self, parent):
        super().__init__(parent)
        _Vispy2DBase.__init__(self)


class VispyOffScreen3DViewer(QOffScreenViewBox, _Vispy3DDensityBase):
    def __init__(self, parent):
        super().__init__(parent)
        _Vispy3DDensityBase.__init__(self)


class VispyNative3DViewer(QNativeViewBox, _Vispy3DDensityBase):
    def __init__(self, parent):
        super().__init__(parent)
        _Vispy3DDensityBase.__init__(self)


class VispyOffScreen3DTomogramViewer(QOffScreenViewBox, _Vispy3DTomogramBase):
    def __init__(self, parent):
        super().__init__(parent)
        _Vispy3DTomogramBase.__init__(self)


class VispyNative3DTomogramViewer(QNativeViewBox, _Vispy3DTomogramBase):
    def __init__(self, parent):
        super().__init__(parent)
        _Vispy3DTomogramBase.__init__(self)


if is_egl_available():
    Vispy2DViewer = VispyOffScreen2DViewer
    Vispy3DViewer = VispyOffScreen3DViewer
    Vispy3DTomogramViewer = VispyOffScreen3DTomogramViewer
else:
    Vispy2DViewer = VispyNative2DViewer
    Vispy3DViewer = VispyNative3DViewer
    Vispy3DTomogramViewer = VispyNative3DTomogramViewer
