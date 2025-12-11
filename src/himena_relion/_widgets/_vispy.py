from __future__ import annotations
from functools import lru_cache
import sys
from timeit import default_timer
import numpy as np
from numpy.typing import NDArray
from qtpy import QtWidgets as QtW, QtCore, QtGui

from vispy import scene, use
from vispy.scene import ViewBox
from vispy.scene.visuals import (
    Image as VispyImage,
    Markers as VispyMarkers,
    Volume as VispyVolume,
)
from vispy.util import keys as VispyKeys

from himena_relion._widgets._qviewbox import QViewBox


def get_qt_app():
    # look for the imported Qt backend
    for libname in ["PyQt5", "PyQt6", "PySide2", "PySide6"]:
        if sys.modules.get(libname, None):
            app = libname.lower()
            break
    else:
        raise RuntimeError("No Qt backend found for Vispy2DViewer.")
    return app


class VispyViewerBase:
    def __init__(self, parent):
        app = get_qt_app()
        _scene = scene.SceneCanvas(keys="interactive", parent=parent, app=app)
        self._scene = _scene
        self._native_qt_widget = _scene.native

    @property
    def native(self) -> QtW.QWidget:
        return self._native_qt_widget


class Vispy2DViewer(VispyViewerBase):
    def __init__(self, parent):
        super().__init__(parent)
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


@lru_cache(maxsize=1)
def get_offscreen_vispy_app() -> str:
    try:
        app = "egl"
        use(app)
    except Exception:
        try:
            app = "osmesa"
            use(app)
        except Exception:
            app = get_qt_app()
            use(app)
    return app


class _Vispy3DBase:
    def __init__(self):
        self._scene = self.make_scene()
        self._camera = scene.ArcballCamera(fov=0)
        viewbox = self._scene.central_widget.add_view()
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
        self._scene.events.mouse_double_click.connect(lambda _: self.auto_fit())

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


class Vispy3DViewer(QViewBox, _Vispy3DBase):
    def __init__(self, parent):
        super().__init__(parent)
        _Vispy3DBase.__init__(self)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding,
            QtW.QSizePolicy.Policy.Expanding,
        )
        self._vispy_mouse_data = {
            "buttons": [],
            "press_event": None,
            "last_event": None,
            "last_mouse_press": None,
        }
        self._last_time = 0.0

    def _update_pixmap(self, *_):
        size = self.size()
        self._store_qpixmap(size)
        self.update()

    def set_iso_threshold(self, value):
        super().set_iso_threshold(value)
        self._update_pixmap()

    @property
    def native(self) -> QtW.QWidget:
        return self

    def make_scene(self):
        return scene.SceneCanvas(
            keys="interactive",
            app=get_offscreen_vispy_app(),
            show=False,
            size=(340, 340),
        )

    def make_pixmap(self, size: QtCore.QSize) -> NDArray[np.uint8]:
        return self._scene.render()

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        vispy_event = self._vispy_mouse_press(
            native=ev,
            pos=self._get_event_xy(ev.pos()),
            button=BUTTONMAP.get(ev.button(), 0),
            modifiers=self._modifiers(ev),
        )
        if not vispy_event.handled:
            ev.ignore()
        self._update_pixmap()

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent):
        vispy_event = self._vispy_mouse_release(
            native=ev,
            pos=self._get_event_xy(ev.pos()),
            button=BUTTONMAP[ev.button()],
            modifiers=self._modifiers(ev),
        )
        if not vispy_event.handled:
            ev.ignore()
        self._update_pixmap()

    def mouseDoubleClickEvent(self, ev: QtGui.QMouseEvent):
        vispy_event = self._vispy_mouse_double_click(
            native=ev,
            pos=self._get_event_xy(ev.pos()),
            button=BUTTONMAP.get(ev.button(), 0),
            modifiers=self._modifiers(ev),
        )
        if not vispy_event.handled:
            ev.ignore()
        self._update_pixmap()

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent):
        # NB ignores events, returns None for events in quick succession
        vispy_event = self._vispy_mouse_move(
            native=ev,
            pos=self._get_event_xy(ev.pos()),
            modifiers=self._modifiers(ev),
        )
        if vispy_event is None or not vispy_event.handled:
            ev.ignore()
        self._update_pixmap()

    def wheelEvent(self, ev: QtGui.QWheelEvent):
        # Get scrolling
        delta = ev.angleDelta()
        deltax, deltay = delta.x() / 120.0, delta.y() / 120.0
        # Emit event
        vispy_event = self._scene.events.mouse_wheel(
            native=ev,
            delta=(deltax, deltay),
            pos=self._get_event_xy(ev.pos()),
            modifiers=self._modifiers(ev),
        )
        if not vispy_event.handled:
            ev.ignore()
        self._update_pixmap()

    def _modifiers(self, event: QtGui.QInputEvent):
        # Convert the QT modifier state into a tuple of active modifier keys.
        mod = ()
        qtmod = event.modifiers()
        for q, v in (
            [QtCore.Qt.KeyboardModifier.ShiftModifier, VispyKeys.SHIFT],
            [QtCore.Qt.KeyboardModifier.ControlModifier, VispyKeys.CONTROL],
            [QtCore.Qt.KeyboardModifier.AltModifier, VispyKeys.ALT],
            [QtCore.Qt.KeyboardModifier.MetaModifier, VispyKeys.META],
        ):
            if qtmod & q:
                mod += (v,)
        return mod

    def _vispy_mouse_press(self, **kwargs):
        # default method for delivering mouse press events to the canvas
        kwargs.update(self._vispy_mouse_data)
        ev = self._scene.events.mouse_press(**kwargs)
        if self._vispy_mouse_data["press_event"] is None:
            self._vispy_mouse_data["press_event"] = ev

        self._vispy_mouse_data["buttons"].append(ev.button)
        self._vispy_mouse_data["last_event"] = ev

        return ev

    def _vispy_mouse_move(self, **kwargs):
        if default_timer() - self._last_time < 0.01:
            return
        self._last_time = default_timer()

        # default method for delivering mouse move events to the canvas
        kwargs.update(self._vispy_mouse_data)

        # Break the chain of prior mouse events if no buttons are pressed
        # (this means that during a mouse drag, we have full access to every
        # move event generated since the drag started)
        if self._vispy_mouse_data["press_event"] is None:
            last_event = self._vispy_mouse_data["last_event"]
            if last_event is not None:
                last_event._forget_last_event()
        else:
            kwargs["button"] = self._vispy_mouse_data["press_event"].button

        ev = self._scene.events.mouse_move(**kwargs)
        self._vispy_mouse_data["last_event"] = ev
        return ev

    def _vispy_mouse_release(self, **kwargs):
        # default method for delivering mouse release events to the canvas
        kwargs.update(self._vispy_mouse_data)

        ev = self._scene.events.mouse_release(**kwargs)
        if (
            self._vispy_mouse_data["press_event"]
            and self._vispy_mouse_data["press_event"].button == ev.button
        ):
            self._vispy_mouse_data["press_event"] = None

        if ev.button in self._vispy_mouse_data["buttons"]:
            self._vispy_mouse_data["buttons"].remove(ev.button)
        self._vispy_mouse_data["last_event"] = ev

        return ev

    def _vispy_mouse_double_click(self, **kwargs):
        # default method for delivering double-click events to the canvas
        kwargs.update(self._vispy_mouse_data)

        ev = self._scene.events.mouse_double_click(**kwargs)
        self._vispy_mouse_data["last_event"] = ev
        return ev

    def _get_event_xy(self, pos: QtCore.QPoint) -> tuple[int, int]:
        posx, posy = pos.x(), pos.y()
        return posx, posy


class VispyNative3DViewer:
    def make_scene(self) -> scene.SceneCanvas:
        app = get_qt_app()
        _scene = scene.SceneCanvas(keys="interactive", app=app)
        self._native_qt_widget = _scene.native
        return _scene

    @property
    def native(self) -> QtW.QWidget:
        return self._native_qt_widget


BUTTONMAP = {
    QtCore.Qt.MouseButton.NoButton: 0,
    QtCore.Qt.MouseButton.LeftButton: 1,
    QtCore.Qt.MouseButton.RightButton: 2,
    QtCore.Qt.MouseButton.MiddleButton: 3,
    QtCore.Qt.MouseButton.BackButton: 4,
    QtCore.Qt.MouseButton.ForwardButton: 5,
}
