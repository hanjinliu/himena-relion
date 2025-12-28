from qtpy import QtWidgets as QtW


class QMicrographListWidget(QtW.QListWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(180)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)

    def set_choices(self, mic_names: list[str]):
        """Set the micrograph choices in the list widget."""
        if self.count() > 0:
            current_text = self.currentItem().text()
        else:
            current_text = None
        self.clear()
        self.addItems(mic_names)
        if current_text and current_text in mic_names:
            ith = mic_names.index(current_text)
            self.setCurrentIndex(ith)
        elif mic_names:
            self.setCurrentRow(0)
