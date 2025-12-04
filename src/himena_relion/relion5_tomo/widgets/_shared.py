from __future__ import annotations
from qtpy import QtWidgets as QtW, QtCore


def standard_layout(widget: QtW.QScrollArea) -> QtW.QVBoxLayout:
    inner = QtW.QWidget()
    widget.setWidget(inner)
    widget.setWidgetResizable(True)
    layout = QtW.QVBoxLayout(inner)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignHCenter
    )
    return layout
