from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore
from himena.qt._qlineedit import QIntLineEdit


class QIntWidget(QtW.QWidget):
    """Integer input widget in X/Xmax format."""

    valueChanged = QtCore.Signal(int)

    def __init__(self, text: str, label_width: int | None = None):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QtW.QLabel(text)
        layout.addWidget(label)
        self._int_edit = QIntLineEdit()
        self._int_edit.setText("0")
        # self._int_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._int_edit.setFixedWidth(40)
        self._max_edit = QtW.QLabel("/0")
        self._max_edit.setFixedWidth(40)
        self._max_edit.setSizePolicy(
            QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self._int_edit)
        layout.addWidget(self._max_edit)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        if label_width:
            label.setFixedWidth(label_width)
        self._int_edit.valueChanged.connect(self._on_value_changed)

    def _on_value_changed(self, value: str):
        if value == "":
            return
        self.valueChanged.emit(int(value))

    def minimum(self) -> int:
        return self._int_edit.minimum()

    def setMinimum(self, value: int):
        self._int_edit.setMinimum(value)
        if int(self._int_edit.text()) < value:
            self._int_edit.setText(str(value))

    def maximum(self) -> int:
        return self._int_edit.maximum()

    def setMaximum(self, value: int):
        self._int_edit.setMaximum(value)
        self._max_edit.setText(f"/{value}")
        if int(self._int_edit.text()) > value:
            self._int_edit.setText(str(value))

    def value(self) -> int:
        return int(self._int_edit.text())

    def setValue(self, value: int):
        self._int_edit.setText(str(value))

    def setRange(self, min_value: int, max_value: int):
        self.setMinimum(min_value)
        self.setMaximum(max_value)
