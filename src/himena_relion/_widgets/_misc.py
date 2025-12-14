from __future__ import annotations

from qtpy import QtWidgets as QtW


def spacer_widget():
    spacer = QtW.QWidget()
    spacer.setSizePolicy(
        QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
    )
    return spacer
