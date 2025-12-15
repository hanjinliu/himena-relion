from __future__ import annotations
from pathlib import Path
import logging
from typing import Iterator
import imodmodel
import pandas as pd
from qtpy import QtWidgets as QtW
import starfile
from himena_relion._widgets import Q2DViewer
from himena_relion import _job

_LOGGER = logging.getLogger(__name__)


class QFindBeads3DViewer(QtW.QWidget):
    def __init__(self, job_dir: _job.ExternalJobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = QtW.QVBoxLayout(self)

        self._viewer = Q2DViewer()
        self._tomo_choice = QtW.QComboBox()
        self._tomo_choice.currentTextChanged.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Tomogram Z slice</b>"))
        layout.addWidget(self._tomo_choice)
        layout.addWidget(self._viewer)
        self.initialize(job_dir)

    def on_job_updated(self, job_dir: _job.ExternalJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".mod":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_id)

    def initialize(self, job_dir: _job.ExternalJobDirectory):
        """Initialize the viewer with the job directory."""
        current_text = self._tomo_choice.currentText()
        items: list[str] = []
        for info in self._iter_tomogram_info():
            items.append(info.tomo_name)
        self._tomo_choice.clear()
        self._tomo_choice.addItems(items)
        if len(items) == 0:
            self._viewer.clear()
        if current_text in items:
            self._tomo_choice.setCurrentText(current_text)
        self._on_tomo_changed(self._tomo_choice.currentText())
        self._viewer.auto_fit()

    def _on_tomo_changed(self, text: str):
        """Update the viewer when the selected tomogram changes."""
        for info in self._iter_tomogram_info():
            if info.tomo_name == text:
                break
        else:
            return
        mod_path = self._job_dir.path / "models" / f"{text}.mod"
        if not mod_path.exists():
            self._viewer.clear()
            return
        tomo_view = info.read_tomogram(self._job_dir.relion_project_dir)
        self._viewer.set_array_view(
            tomo_view,
            self._viewer._last_clim,
        )
        mod_data = imodmodel.read(mod_path)
        self._viewer.set_points(mod_data[["z", "y", "x"]].to_numpy())

    def _iter_tomogram_info(self) -> Iterator[_job.TomogramInfo]:
        pipe = self._job_dir.parse_job_pipeline()
        input0 = pipe.get_input_by_type("TomogramGroupMetadata")
        assert input0 is not None
        df_tomo = starfile.read(input0.path)
        assert isinstance(df_tomo, pd.DataFrame)
        for _, row in df_tomo.iterrows():
            yield _job.TomogramInfo.from_series(row)
