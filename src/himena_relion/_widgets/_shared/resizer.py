from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui


class QResizer(QtW.QFrame):
    """Resizer that resize the widget upper it when the widget is resized."""

    def __init__(self, widget: QtW.QWidget):
        super().__init__()
        self.setFrameShape(QtW.QFrame.Shape.HLine)
        self.setFrameShadow(QtW.QFrame.Shadow.Sunken)
        self._drag_start = QtCore.QPoint()
        self._dragging = False
        self._widget = widget
        self.setCursor(QtCore.Qt.CursorShape.SizeVerCursor)
        self.setFixedHeight(6)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPos()
            self._dragging = True

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self._dragging:
            delta = event.globalPos() - self._drag_start
            self._drag_start = event.globalPos()
            new_size = self._widget.size() + QtCore.QSize(0, delta.y())
            dh = new_size.height() - self._widget.minimumHeight()
            if dh < 0:
                return
            self._widget.resize(new_size)

            parent = self._widget.parentWidget()
            new_size = parent.size() + QtCore.QSize(0, delta.y())
            parent.resize(new_size)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._dragging = False
        self._drag_start = QtCore.QPoint()
