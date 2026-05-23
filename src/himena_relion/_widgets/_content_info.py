from __future__ import annotations

from pathlib import Path
from typing import overload
from superqt.utils import thread_worker, GeneratorWorker
from qtpy import QtWidgets as QtW, QtCore
from himena_relion._utils import bytes_to_size_str, iter_directory_content_summary

create_worker = thread_worker(iter_directory_content_summary)


class QJobContentInfo(QtW.QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._worker: GeneratorWorker | None = None
        self.clear_content_info()

    @overload
    def set_content_info(self, num_files: tuple[int, int]): ...
    @overload
    def set_content_info(self, num_files: int, total_size_bytes: int): ...
    def set_content_info(
        self, num_files: int | tuple[int, int], total_size_bytes: int = -1
    ):
        if isinstance(num_files, tuple):
            num_files, total_size_bytes, *_ = num_files
        self.setText(f"{num_files} files, {bytes_to_size_str(total_size_bytes)}")

    def count_directory_content(self, path: Path):
        """Start counting the directory content in a separate thread."""
        self.reset_worker()
        self._worker = create_worker(path)
        self._worker.yielded.connect(self.set_content_info)
        self._worker.start()

    def clear_content_info(self):
        self.setText(" -- files, -- KB")
        self.reset_worker()

    def closeEvent(self, a0):
        self.reset_worker()
        return super().closeEvent(a0)

    def reset_worker(self):
        if self._worker is not None:
            self._worker.quit()
            self._worker = None
