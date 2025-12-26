from __future__ import annotations

from qtpy import QtWidgets as QtW


class QNumParticlesLabel(QtW.QLabel):
    """A QLabel to show the number of particles."""

    def __init__(self):
        super().__init__()
        self.setText("--- particles")

    def set_number(self, num: int):
        if num >= 0:
            self.setText(f"<b>{num}</b> particles")
        else:
            self.setText("??? particles")
