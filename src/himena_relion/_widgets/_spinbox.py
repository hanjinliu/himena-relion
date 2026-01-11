from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui
from himena.qt._qlineedit import QIntLineEdit

from himena_relion._utils import monospace_font_family


class QIntWidget(QtW.QWidget):
    """Integer input widget in X/Xmax format."""

    valueChanged = QtCore.Signal(int)

    def __init__(self, text: str, label_width: int | None = None):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        label = QtW.QLabel(text)
        layout.addWidget(label)
        self._int_edit = QIntLineEdit()
        self._int_edit.setText("0")
        self._int_edit.setFixedSize(40, 16)
        self._max_edit = QtW.QLabel(" /0")
        self._max_edit.setFixedSize(40, 16)
        self._max_edit.setSizePolicy(
            QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Fixed
        )
        self._left_btn = spin_button("<", self._decrement)
        self._right_btn = spin_button(">", self._increment)
        layout.addWidget(self._left_btn)
        layout.addWidget(self._int_edit)
        layout.addWidget(self._right_btn)
        layout.addWidget(self._max_edit)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        if label_width:
            label.setFixedWidth(label_width)
        self._int_edit.valueChanged.connect(self._on_value_changed)

    def _increment(self):
        """Increment the value by 1."""
        current_value = self.value()
        if current_value < self.maximum():
            self.setValue(current_value + 1)

    def _decrement(self):
        """Decrement the value by 1."""
        current_value = self.value()
        if current_value > self.minimum():
            self.setValue(current_value - 1)

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


def spin_button(char: str, callback) -> QtW.QPushButton:
    button = QtW.QToolButton()
    button.setText(char)
    button.setFixedWidth(12)
    button.setFont(QtGui.QFont(monospace_font_family()))
    button.setStyleSheet("color: gray;")
    button.clicked.connect(callback)
    button.setToolTip(callback.__doc__)
    return button


class QIntChoiceWidget(QIntWidget):
    current_changed = QtCore.Signal(int)

    def __init__(self, text: str, label_width: int | None = None):
        super().__init__(text, label_width)
        self.valueChanged.connect(self._on_iter_changed)
        self._choices: list[int] = []
        self._iter_current_value = 0

    def set_choices(self, choices: list[int]):
        self._choices = choices
        if choices:
            self.setMaximum(max(choices))
            self.setMinimum(min(choices))
            self.setValue(max(choices))
            self._iter_current_value = max(choices)
        else:
            self.setMaximum(0)
            self.setMinimum(0)
            self.setValue(0)
        self._on_iter_changed(self._iter_current_value)

    def _on_iter_changed(self, value: int):
        niter_list = self._choices
        if len(niter_list) == 0:
            return
        if value in niter_list:
            self._iter_current_value = value
            self.current_changed.emit(value)
        else:
            if value > self._iter_current_value:
                next_iters = [n for n in niter_list if n > self._iter_current_value]
                if next_iters:
                    nearest_iter = min(next_iters)
                else:
                    nearest_iter = max(niter_list)
            else:
                prev_iters = [n for n in niter_list if n < self._iter_current_value]
                if prev_iters:
                    nearest_iter = max(prev_iters)
                else:
                    nearest_iter = min(niter_list)
            self.setValue(nearest_iter)
