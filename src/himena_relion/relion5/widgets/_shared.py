from qtpy import QtWidgets as QtW, QtCore


class QMicrographListWidget(QtW.QTableWidget):
    current_changed = QtCore.Signal(tuple)

    def __init__(self, columns: list[str] = ("Micrograph",)):
        super().__init__()
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QtW.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(list(columns))
        self.horizontalHeader().setVisible(len(columns) > 1)
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def set_choices(self, choices: list[tuple[str, ...]]):
        """Set the micrograph choices in the list widget."""
        if self.rowCount() > 0 and self.currentItem():
            current_text = self.item(self.currentRow(), 0).text()
        else:
            current_text = None
        self.setRowCount(0)
        self.setRowCount(len(choices))
        choices_0 = []
        for i, entry in enumerate(choices):
            for j, name in enumerate(entry):
                self.setItem(i, j, QtW.QTableWidgetItem(name))
            choices_0.append(entry[0])
        if current_text and current_text in current_text:
            ith = current_text.index(current_text)
            self.setCurrentCell(ith, 0)
        elif choices:
            self.setCurrentCell(0, 0)
        self.resizeColumnsToContents()

    def _on_selection_changed(self):
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            to_emit = tuple(
                self.item(selected_rows[0].row(), col).text()
                for col in range(self.columnCount())
            )
            self.current_changed.emit(to_emit)
