from __future__ import annotations
from pathlib import Path

import logging
from qtpy import QtWidgets as QtW, QtGui
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    QIntWidget,
    spacer_widget,
)
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job(_job_dir.Class3DJobDirectory)
class QClass3DViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._text_edit = QtW.QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)

        self._viewer = Q3DViewer()
        self._class_choice = QIntWidget("Class", label_width=50)
        self._iter_choice = QIntWidget("Iteration", label_width=60)
        self._class_choice.setMinimum(1)
        self._iter_choice.setMinimum(0)
        hor_layout0 = QtW.QHBoxLayout()
        hor_layout0.addWidget(self._viewer)
        hor_layout0.addWidget(self._text_edit)
        self._layout.addLayout(hor_layout0)
        hor_layout1 = QtW.QHBoxLayout()
        hor_layout1.addWidget(self._iter_choice)
        hor_layout1.addWidget(self._class_choice)
        hor_layout1.setContentsMargins(0, 0, 0, 0)
        self._layout.addLayout(hor_layout1)
        self._index_start = 1
        self._job_dir: _job_dir.Class3DJobDirectory | None = None

        self._iter_choice.valueChanged.connect(self._on_iter_changed)
        self._class_choice.valueChanged.connect(self._on_class_changed)
        self._layout.addWidget(spacer_widget())

    def on_job_updated(self, job_dir: _job_dir.Class3DJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).name.endswith("_model.star"):
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", self._job_dir.job_id)

    def initialize(self, job_dir: _job_dir.Class3DJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        nclasses = job_dir.num_classes()
        if nclasses == 0:
            return
        niters = job_dir.num_iters()
        self._class_choice.setMaximum(nclasses)
        self._iter_choice.setMaximum(max(niters - 1, 0))
        self._iter_choice.setValue(self._iter_choice.maximum())
        self._on_iter_changed(self._iter_choice.value())
        self._viewer.auto_threshold()
        self._viewer.auto_fit()

    def _on_iter_changed(self, value: int):
        self._update_for_value(value, self._class_choice.value())
        self._text_edit.clear()
        self._print_summary_table(value)

    def _on_class_changed(self, value: int):
        self._update_for_value(self._iter_choice.value(), value)

    def _update_for_value(self, niter: int, class_id: int):
        res = self._job_dir.get_result(niter)
        map0 = res.class_map(class_id - self._index_start)
        self._viewer.set_image(map0)

    def _print_summary_table(self, niter):
        cursor = self._text_edit.textCursor()
        res = self._job_dir.get_result(niter)
        df = res.summary_dataframe()
        if df is None:
            return

        nclasses = len(df)
        if texttable := cursor.insertTable(nclasses + 1, 3):
            _insert(texttable, 0, 0, "Class")
            _insert(texttable, 0, 1, "Distribution")
            _insert(texttable, 0, 2, "Resolution")
            for ith in range(nclasses):
                _insert(texttable, ith + 1, 0, str(ith + 1))
                _insert(texttable, ith + 1, 1, f"{df.iloc[ith, 1]:.2%}")
                _insert(texttable, ith + 1, 2, f"{df.iloc[ith, 4]:.2f} Å")
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.insertText("\n\n")


def _insert(texttable: QtGui.QTextTable, row: int, col: int, text: str):
    texttable.cellAt(row, col).firstCursorPosition().insertText(text)
