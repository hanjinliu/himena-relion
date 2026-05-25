from __future__ import annotations
from pathlib import Path
import logging

from qtpy import QtWidgets as QtW
from starfile_rs import read_star
from himena.core import create_dataframe_model
from himena.widgets import current_instance
from himena_builtins.qt.dataframe import QDataFrameView

from himena_relion._widgets import QJobScrollArea, register_job
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job("relion.joinstar")
class QJoinParticleViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        self._initialized = False
        self._top_label = QtW.QLabel("Nothing imported yet.")
        self._combobox = QtW.QComboBox()
        self._combobox.currentTextChanged.connect(self._on_combobox_changed)
        self._combobox.setMaximumWidth(180)
        self._df_view = QDataFrameView(current_instance())
        self._star_path: Path | None = None
        self._layout.addWidget(self._top_label)
        self._layout.addWidget(self._combobox)
        self._layout.addWidget(self._df_view)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        if self._initialized:
            return
        matched_files = list(job_dir.path.glob("join_*.star"))
        if len(matched_files) == 0:
            self._star_path = matched_files[0]
            star = read_star(self._star_path)
            self._combobox.addItems(list(star.keys()))
            self._combobox.setCurrentIndex(0)
            self._initialized = True

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix not in [".out", ".err"]:
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def _on_combobox_changed(self, text: str):
        if text and self._star_path and self._star_path.exists():
            if block := read_star(self._star_path).get(text):
                self._df_view.update_model(create_dataframe_model(block.to_polars()))
