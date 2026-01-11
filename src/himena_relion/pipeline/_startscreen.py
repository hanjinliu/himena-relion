from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from qtpy import QtGui, QtWidgets as QtW, QtCore
from himena import MainWindow

if TYPE_CHECKING:
    from himena_relion._job_class import RelionJob


class QRelionPipelineStartScreen(QtW.QWidget):
    """Start screen widget for RELION pipeline."""

    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui = ui
        layout = QtW.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        label_spa = QtW.QLabel("<b>Single Particle Analysis</b>")
        label_tomo = QtW.QLabel("<b>Tomography</b>")
        font = label_spa.font()
        font.setPointSize(14)
        label_spa.setFont(font)
        label_tomo.setFont(font)

        if "himena_relion.relion5" in sys.modules:
            # RELION SPA plugin is imported
            from himena_relion.relion5._builtins import (
                ImportMoviesJob,
                ImportMicrographsJob,
            )

            self._spa_movies_btn = self._make_btn(ImportMoviesJob)
            self._spa_micrographs_btn = self._make_btn(ImportMicrographsJob)
            layout.addWidget(label_spa)
            layout.addWidget(self._spa_movies_btn)
            layout.addWidget(self._spa_micrographs_btn)

        if "himena_relion.relion5_tomo" in sys.modules:
            # RELION Tomography plugin is imported
            from himena_relion.relion5_tomo._builtins import (
                ImportTomoJob,
                ImportTomoMicrographsJob,
            )

            self._tomo_movies_btn = self._make_btn(ImportTomoJob)
            self._tomo_micrographs_btn = self._make_btn(ImportTomoMicrographsJob)
            layout.addSpacing(20)
            layout.addWidget(label_tomo)
            layout.addWidget(self._tomo_movies_btn)
            layout.addWidget(self._tomo_micrographs_btn)

    def _make_btn(self, job_cls: type[RelionJob]):
        button = QtW.QPushButton(job_cls.job_title())
        button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        button.clicked.connect(lambda: self._ui.exec_action(job_cls.command_id()))
        if tooltip := getattr(job_cls, "__doc__", None):
            button.setToolTip(tooltip)
        return button
