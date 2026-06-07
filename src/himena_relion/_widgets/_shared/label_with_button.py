from __future__ import annotations
from typing import Callable

from qtpy import QtWidgets as QtW, QtCore
from himena.qt import QColoredToolButton


class QLabelWithButtons(QtW.QWidget):
    """A widget that contains a label and a button on the right side of the label."""

    def __init__(
        self,
        label: str,
        buttons: list[tuple[str, Callable[[], None]]],
        width: int = 360,
    ):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtW.QLabel(label), stretch=10)
        self.setFixedWidth(width)
        tool_buttons = []
        for btn_svg, callback in buttons:
            btn = QColoredToolButton(callback, btn_svg)
            btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(20, 20)
            btn.update_color("gray")
            if doc := getattr(callback, "__doc__", None):
                btn.setToolTip(doc)
                btn.setStatusTip(doc)
            tool_buttons.append(btn)
            layout.addWidget(btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self._buttons: list[QColoredToolButton] = tool_buttons
