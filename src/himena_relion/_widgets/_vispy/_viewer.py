from __future__ import annotations
from functools import lru_cache
from typing import Literal
import numpy as np
from numpy.typing import NDArray
from psygnal import Signal
from PIL import Image
from qtpy import QtWidgets as QtW

from vispy import scene, use
from vispy.scene import ViewBox
from vispy.scene.visuals import (
    Image as VispyImage,
    Markers as VispyMarkers,
    Volume as VispyVolume,
    Arrow as VispyArrow,
)
from vispy.app import MouseEvent
from vispy.visuals.transforms import STTransform
from himena.widgets import set_clipboard, current_instance
from himena_relion._image_readers import ArrayFilteredView
from himena_relion._widgets._vispy._viewbox import (
    QOffScreenViewBox,
    QNativeViewBox,
    ArcballCamera,
)
from himena_relion._widgets._vispy.motion import MotionPath
from himena_relion._impl_objects import TubeObject


@lru_cache(maxsize=1)
def is_egl_available() -> bool:
    try:
        use("egl")
        return True
    except Exception:
        return False


def prepare_opengl_window(window: QtW.QWidget) -> None:
    """Switch the top-level window to OpenGL composition in advance.

    When the first QOpenGLWidget (the native vispy canvas) is added to a window, Qt
    has to recreate the native window to switch it to OpenGL composition, which makes
    the main window disappear and reappear (very visible on Windows). Adding a hidden
    QOpenGLWidget forces this to happen now (at startup) instead of when the first
    vispy canvas is created. Nothing is needed for the offscreen EGL rendering.
    """
    if is_egl_available():
        return
    from qtpy.QtOpenGLWidgets import QOpenGLWidget

    # The hidden widget is kept as a child, so that the window is never switched back.
    # It is never shown, so no OpenGL context is created for it.
    dummy = QOpenGLWidget(window)
    dummy.setObjectName("himena_relion_opengl_warmup")
    dummy.setFixedSize(0, 0)
    dummy.hide()


class _VispyBase:
    right_clicked = Signal()

    def __init__(self):
        self._scene = self.make_scene()
        self._scene.events.mouse_press.connect(self._on_mouse_press)
        self._scene.events.mouse_release.connect(self._on_mouse_release)

    def make_scene(self) -> scene.SceneCanvas:
        raise NotImplementedError

    def copy_screenshot(self):
        img = self._scene.render()
        _img_copy = np.array(img)
        set_clipboard(image=_img_copy)
        self._img_copy = _img_copy  # Keep a reference to prevent garbage collection

    def save_screenshot(self):
        img = self._scene.render()
        path = current_instance().exec_file_dialog("w", extension_default=".png")
        if path is not None:
            Image.fromarray(img).save(path)

    def _event_to_canvas_scale(self) -> float:
        """Ratio of the canvas coordinates to the mouse event positions."""
        return 1.0

    def _on_mouse_press(self, event: MouseEvent):
        pass

    def _on_mouse_release(self, event: MouseEvent):
        if (
            isinstance(last := event.last_event, MouseEvent)
            and last.type == "mouse_press"
            and last.button == 2
            and np.sum(np.abs(last.pos - event.pos)) < 5
        ):
            self.right_clicked.emit()


class _Vispy2DBase(_VispyBase):
    def __init__(self):
        super().__init__()
        viewbox = self._scene.central_widget.add_view(camera="panzoom")
        assert isinstance(viewbox, ViewBox)
        self._viewbox = viewbox

        # initialize camera
        self._viewbox.camera.aspect = 1.0
        self._viewbox.camera.flip = (False, False, False)

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


class _Vispy3DBase(_VispyBase):
    _volume_visual: VispyVolume

    def __init__(self):
        super().__init__()
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
        c0, c1 = clim
        self._volume_visual.clim = float(c0), float(c1)

    def auto_fit(self):
        self._camera.fit_to_shape(self._image_data.shape)


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
        self._arrow_visual.visible = False
        self._arrows_visible = False
        self._has_arrows = False
        self._iso_threshold = 0.5

    @property
    def arrow_visual(self) -> VispyArrow:
        return self._arrow_visual

    @property
    def arrows_visible(self) -> bool:
        """Whether the arrows are requested to be shown."""
        return self._arrows_visible

    @arrows_visible.setter
    def arrows_visible(self, visible: bool):
        self._arrows_visible = bool(visible)
        self._update_arrow_visibility()

    def _update_arrow_visibility(self):
        # vispy raises an error when drawing an arrow visual without any data, which
        # breaks the rendering of the whole canvas (the off-screen canvas becomes
        # completely transparent). Keep the visual hidden while there is no arrow.
        self._arrow_visual.visible = self._arrows_visible and self._has_arrows

    def set_rendering_mode(self, mode: str):
        mode = mode.title()
        if mode == "Surface":
            self._volume_visual.method = "iso"
            self._volume_visual.set_gl_state(preset="opaque")
        elif mode == "Maximum":
            self._volume_visual.method = "mip"
            self._volume_visual.set_gl_state(preset="translucent")
        elif mode == "Average":
            self._volume_visual.method = "average"
            self._volume_visual.set_gl_state(preset="translucent")
        else:  # pragma: no cover
            raise ValueError(f"Unknown rendering mode: {mode}")

    def set_iso_threshold(self, value):
        self._iso_threshold = value
        _min, _max = self._lims
        self._volume_visual.threshold = (value - _min) / (_max - _min)
        self._volume_visual.update()

    def set_arrows(self, tubes: list[TubeObject]):
        if len(tubes) == 0:
            # Empty data cannot be drawn by vispy. Just hide the visual.
            self._has_arrows = False
            self._update_arrow_visibility()
            return
        # NOTE: Vispy Arrow is in xyz order.
        starts = np.stack([tube.start for tube in tubes], axis=0)
        ends = np.stack([tube.end for tube in tubes], axis=0)
        # vispy raises an error for color values out of [0, 1] at draw time
        arrow_colors = np.clip(
            np.stack([tube.color for tube in tubes], axis=0), 0.0, 1.0
        ).astype(np.float32)
        arrows = np.concatenate([starts, ends], axis=1).astype(np.float32)
        # positions and colors of each line segment: start0, end0, start1, end1, ...
        pos = arrows.reshape(-1, 3)
        colors = np.repeat(arrow_colors, 2, axis=0)
        self._arrow_visual.set_data(
            pos=pos,
            color=colors,
            width=2.0,
            connect="segments",
            arrows=arrows,
        )
        self._arrow_visual.arrow_color = arrow_colors
        self._has_arrows = True
        self._update_arrow_visibility()


class _Vispy3DTomogramBase(_Vispy3DBase):
    """Vispy canvas for 3D tomogram visualization."""

    plane_position_changed = Signal(int)

    # Spheres at the corners of the plane, used as handles to move the plane.
    _HANDLE_SIZE = 14.0  # diameter in logical pixels
    _HANDLE_COLOR = "#FFA726"

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
        self._volume_visual.set_gl_state(preset="translucent")
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

        self._plane_handles = VispyMarkers(
            pos=np.zeros((4, 3), dtype=np.float32), spherical=True, scaling="fixed",
            parent=self._viewbox.scene,
        )  # fmt: skip
        # Always draw the handles on top of the plane so that they can be grabbed.
        self._plane_handles.update_gl_state(depth_test=False)
        self._plane_handles.order = 10
        self._plane_handles.visible = False
        self._plane_handle_pos = np.zeros((4, 3), dtype=np.float32)
        self._dragging_plane_handle = False

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

    @property
    def plane_handles_visual(self) -> VispyMarkers:
        """Spheres at the plane corners that move the plane when dragged."""
        return self._plane_handles

    def set_plane_position(self, zpos: int):
        zpos = max(0, min(self._array_view_nz - 1, zpos))
        arr_2d = self._array_view.get_slice(zpos)
        self._current_image_slice = arr_2d
        self._volume_visual.set_data(arr_2d[np.newaxis], copy=False)
        self._volume_visual.transform = STTransform(translate=(0, 0, zpos))
        self._volume_visual.plane_position = [0, 0, zpos]
        self._plane_position = zpos
        self._update_plane_handles()
        self.plane_position_changed.emit(zpos)
        self._volume_visual.update()

    def _update_plane_handles(self):
        """Place the handles at the four corners of the displayed plane."""
        ny, nx = self._current_image_slice.shape
        d = 4
        x0, y0, x1, y1 = -d, -d, nx - d, ny - d
        z = self._plane_position
        pos = np.array(
            [[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]], dtype=np.float32
        )
        self._plane_handle_pos = pos
        self._plane_handles.set_data(
            pos,
            size=self._HANDLE_SIZE * self._event_to_canvas_scale(),
            edge_width=0,
            face_color=self._HANDLE_COLOR,
        )
        self._plane_handles.visible = True

    def _is_on_plane_handle(self, event_pos) -> bool:
        """True if the mouse event position is on one of the plane handles."""
        if not (self._plane_handles.visible and self._volume_visual.visible):
            return False
        scale = self._event_to_canvas_scale()
        # world coordinates -> canvas coordinates
        tr = self._viewbox.scene.node_transform(self._scene.scene)
        mapped = tr.map(self._plane_handle_pos)
        handle_xy = mapped[:, :2] / mapped[:, 3:4]
        dist = np.linalg.norm(handle_xy - np.asarray(event_pos[:2]) * scale, axis=1)
        radius = (self._HANDLE_SIZE / 2 + 2) * scale  # small margin for easy grab
        return bool(np.any(dist <= radius))

    def _on_mouse_press(self, event: MouseEvent):
        if event.button == 1 and self._is_on_plane_handle(event.pos):
            self._dragging_plane_handle = True
            # Mark handled so that the Qt event is accepted, and block the event so
            # that the canvas does not pass it to the camera (no rotation).
            event.handled = True
            event.blocked = True

    def _on_mouse_move(self, event: MouseEvent):
        if self._dragging_plane_handle:
            event.handled = True
            event.blocked = True
        elif not (event.button == 1 and "control" in event.modifiers):
            return
        if (events := event.drag_events()) and len(events) >= 2:
            prev = events[-2]
            new = events[-1]
            xy = new.pos - prev.pos
            speed = 1
            zpos = int(self._plane_position - xy[1] * speed)
            self.set_plane_position(zpos)

    def _on_mouse_release(self, event: MouseEvent):
        if event.button == 1:
            self._dragging_plane_handle = False
        super()._on_mouse_release(event)

    def auto_fit(self):
        if self._array_view is None:
            return
        nz = self._array_view_nz
        ny, nx = self._array_view.get_shape()
        self._camera.fit_to_shape((nx, ny, nz))


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
