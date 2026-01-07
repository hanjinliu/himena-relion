# Some parts of this code are adapted from the Vispy library, under the
# following licensing terms.

# Vispy licensing terms
# ---------------------

# Vispy is licensed under the terms of the (new) BSD license:

# Copyright (c) 2013-2025, Vispy Development Team. All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * Neither the name of Vispy Development Team nor the names of its
#   contributors may be used to endorse or promote products
#   derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER
# OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


# Exceptions
# ----------

# The examples code in the examples directory can be considered public
# domain, unless otherwise indicated in the corresponding source file.

from __future__ import annotations
from functools import lru_cache
import sys
from timeit import default_timer
import numpy as np
from numpy.typing import NDArray
from qtpy import QtWidgets as QtW, QtCore, QtGui

from vispy import scene
from vispy.app import MouseEvent
from vispy.util import keys as VispyKeys
from vispy.util.quaternion import Quaternion
from psygnal import Signal

from himena.qt import QViewBox


@lru_cache(maxsize=1)
def get_qt_app():
    # look for the imported Qt backend
    for libname in ["PyQt5", "PyQt6", "PySide2", "PySide6"]:
        if sys.modules.get(libname, None):
            app = libname.lower()
            break
    else:
        raise RuntimeError("No Qt backend found for vispy viewer.")
    return app


class QOffScreenViewBox(QViewBox):
    """Vispy viewer widget using offscreen rendering to a QPixmap.

    3D rendering is extremely slow when vispy is used via SSH with X11 forwarding,
    because OpenGL uses the fallback software rendering (llvmpipe) that runs on CPU.
    This class uses offscreen rendering by EGL on the server side to avoid this issue.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding,
            QtW.QSizePolicy.Policy.Expanding,
        )
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.WheelFocus)
        self._vispy_mouse_data = {
            "buttons": [],
            "press_event": None,
            "last_event": None,
            "last_mouse_press": None,
        }
        self._last_time = 0.0

    @property
    def native(self) -> QtW.QWidget:
        return self

    def make_scene(self):
        return scene.SceneCanvas(
            keys="interactive",
            app="egl",
            show=False,
            size=(340, 340),
        )

    def make_pixmap(self, size: QtCore.QSize) -> NDArray[np.uint8]:
        return self._scene.render()

    def _update_pixmap(self, *_):
        size = self.size()
        self._store_qpixmap(size)
        self.update()

    def update_canvas(self):
        self._update_pixmap()

    def resizeEvent(self, a0: QtGui.QResizeEvent):
        ratio = self.devicePixelRatioF()
        # Both scene and viewbox need to be resized
        self._scene.size = (
            int(ratio * a0.size().width()),
            int(ratio * a0.size().height()),
        )
        self._viewbox.size = self._scene.size
        self.camera.viewbox_resize_event(None)
        return super().resizeEvent(a0)

    def closeEvent(self, event):
        self._scene.close()
        return super().closeEvent(event)

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
        ev.accept()

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

    def _vispy_mouse_move(self, **kwargs) -> MouseEvent:
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

    def _vispy_mouse_release(self, **kwargs) -> MouseEvent:
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

    def _vispy_mouse_double_click(self, **kwargs) -> MouseEvent:
        # default method for delivering double-click events to the canvas
        kwargs.update(self._vispy_mouse_data)

        ev = self._scene.events.mouse_double_click(**kwargs)
        self._vispy_mouse_data["last_event"] = ev
        return ev

    def _get_event_xy(self, pos: QtCore.QPoint) -> tuple[int, int]:
        posx, posy = pos.x(), pos.y()
        return posx, posy


class QNativeViewBox:
    def __init__(self, parent):
        self._parent = parent

    def make_scene(self) -> scene.SceneCanvas:
        app = get_qt_app()
        _scene = scene.SceneCanvas(keys="interactive", app=app, parent=self._parent)
        self._native_qt_widget = _scene.native
        return _scene

    @property
    def native(self) -> QtW.QWidget:
        return self._native_qt_widget

    def update_canvas(self):
        pass


class ArcballCamera(scene.ArcballCamera):
    changed = Signal()

    def viewbox_mouse_event(self, event):
        # enable translation with middle mouse button
        super().viewbox_mouse_event(event)
        if event.handled or not self.interactive:
            return

        if event.type == "mouse_move":
            if event.press_event is None:
                return
            p1 = event.mouse_event.press_event.pos
            p2 = event.mouse_event.pos

            if 3 in event.buttons:
                # Translate
                norm = np.mean(self._viewbox.size)
                if self._event_value is None or len(self._event_value) == 2:
                    self._event_value = self.center
                dist = (p1 - p2) / norm * self._scale_factor
                dist[1] *= -1
                # Black magic part 1: turn 2D into 3D translations
                dx, dy, dz = self._dist_to_trans(dist)
                # Black magic part 2: take up-vector and flipping into account
                ff = self._flip_factors
                up, forward, right = self._get_dim_vectors()
                dx, dy, dz = right * dx + forward * dy + up * dz
                dx, dy, dz = ff[0] * dx, ff[1] * dy, dz * ff[2]
                c = self._event_value
                self.center = c[0] + dx, c[1] + dy, c[2] + dz

    def view_changed(self):
        super().view_changed()
        self.changed.emit()

    @property
    def quaternion(self) -> Quaternion:
        return self._quaternion


BUTTONMAP = {
    QtCore.Qt.MouseButton.NoButton: 0,
    QtCore.Qt.MouseButton.LeftButton: 1,
    QtCore.Qt.MouseButton.RightButton: 2,
    QtCore.Qt.MouseButton.MiddleButton: 3,
    QtCore.Qt.MouseButton.BackButton: 4,
    QtCore.Qt.MouseButton.ForwardButton: 5,
}
