import time
import numpy as np
from qtpy import QtCore, QtGui, QtWidgets as QtW
from pytestqt.qtbot import QtBot
from himena_relion._image_readers import ArrayFilteredView
from himena_relion._widgets import Q3DTomogramViewer

LEFT = QtCore.Qt.MouseButton.LeftButton
NO_BUTTON = QtCore.Qt.MouseButton.NoButton
NO_MOD = QtCore.Qt.KeyboardModifier.NoModifier
CTRL = QtCore.Qt.KeyboardModifier.ControlModifier


def _send_mouse(widget: QtW.QWidget, etype, pos, button, buttons, modifiers):
    p = QtCore.QPointF(*pos)
    ev = QtGui.QMouseEvent(etype, p, widget.mapToGlobal(p), button, buttons, modifiers)
    QtW.QApplication.sendEvent(widget, ev)


def _drag(widget: QtW.QWidget, start, dy: int, modifiers=NO_MOD):
    """Vertical left-drag by `dy` pixels in 1-pixel steps."""
    x, y = start
    T = QtCore.QEvent.Type
    _send_mouse(widget, T.MouseButtonPress, (x, y), LEFT, LEFT, modifiers)
    step = 1 if dy > 0 else -1
    for i in range(1, abs(dy) + 1):
        time.sleep(0.012)  # mouse move events within 10 ms are dropped
        _send_mouse(widget, T.MouseMove, (x, y + step * i), NO_BUTTON, LEFT, modifiers)
    _send_mouse(widget, T.MouseButtonRelease, (x, y + dy), LEFT, NO_BUTTON, modifiers)


def _handle_event_pos(viewer: Q3DTomogramViewer, index: int) -> tuple[float, float]:
    canvas = viewer._canvas
    tr = canvas._viewbox.scene.node_transform(canvas._scene.scene)
    mapped = tr.map(canvas._plane_handle_pos[index])
    xy = mapped[:2] / mapped[3] / canvas._event_to_canvas_scale()
    return round(xy[0]), round(xy[1])


def _quat(viewer: Q3DTomogramViewer):
    q = viewer._canvas.camera._quaternion
    return np.array([q.w, q.x, q.y, q.z])


def test_tomogram_plane_handles(qtbot: QtBot):
    viewer = Q3DTomogramViewer()
    qtbot.addWidget(viewer)
    viewer.resize(400, 400)
    arr = np.random.default_rng(0).normal(size=(40, 60, 80)).astype(np.float32)
    viewer.set_array_view(ArrayFilteredView.from_array(arr))
    viewer.auto_fit()
    canvas = viewer._canvas
    widget = canvas.native

    # handles are at the four corners of the plane
    assert canvas.plane_handles_visual.visible
    z0 = canvas._plane_position
    assert z0 == 19
    d = 4
    np.testing.assert_allclose(
        canvas._plane_handle_pos,
        [[-d, -d, z0], [80 - d, -d, z0], [80 - d, 60 - d, z0], [-d, 60 - d, z0]],
    )

    # dragging a handle upward moves the plane up without rotating the camera
    # (the first move after the press is not counted, same as Ctrl + drag)
    quat0 = _quat(viewer)
    _drag(widget, _handle_event_pos(viewer, 1), -10)
    assert canvas._plane_position == z0 + 9
    np.testing.assert_allclose(_quat(viewer), quat0)
    np.testing.assert_allclose(canvas._plane_handle_pos[:, 2], z0 + 9)
    assert not canvas._dragging_plane_handle

    # dragging a handle downward
    _drag(widget, _handle_event_pos(viewer, 3), 5)
    assert canvas._plane_position == z0 + 5
    np.testing.assert_allclose(_quat(viewer), quat0)

    # Ctrl + drag still works
    _drag(widget, (2, 2), -4, modifiers=CTRL)
    assert canvas._plane_position == z0 + 8
    np.testing.assert_allclose(_quat(viewer), quat0)

    # dragging elsewhere rotates the camera and does not move the plane
    _drag(widget, (2, 2), 20)
    assert canvas._plane_position == z0 + 8
    assert not np.allclose(_quat(viewer), quat0)

    # hidden handles cannot be grabbed
    viewer.clear()
    assert not canvas.plane_handles_visual.visible
    quat1 = _quat(viewer)
    _drag(widget, _handle_event_pos(viewer, 1), -10)
    assert canvas._plane_position == z0 + 8
    assert not np.allclose(_quat(viewer), quat1)
