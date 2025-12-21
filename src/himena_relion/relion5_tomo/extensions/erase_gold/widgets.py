from __future__ import annotations
from pathlib import Path
import logging
from typing import Iterator
import imodmodel
import mrcfile
import numpy as np
import pandas as pd
from qtpy import QtWidgets as QtW, QtCore
import starfile
from himena_relion._image_readers import ArrayFilteredView
from himena_relion._widgets import Q2DViewer, Q2DFilterWidget
from himena_relion import _job

_LOGGER = logging.getLogger(__name__)


class QFindBeads3DViewer(QtW.QWidget):
    def __init__(self, job_dir: _job.ExternalJobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = QtW.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self._viewer = Q2DViewer()
        self._viewer.setMaximumHeight(480)
        self._tomo_choice = QtW.QComboBox()
        self._tomo_choice.currentTextChanged.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Tomogram Z slice with fiducials</b>"))
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
            self._viewer.redraw()
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
            self._viewer.redraw()
            return
        tomo_view = info.read_tomogram(self._job_dir.relion_project_dir)
        self._viewer.set_array_view(
            tomo_view,
            self._viewer._last_clim,
        )
        mod_data = imodmodel.read(mod_path)
        bead_size = float(self._job_dir.get_job_param("gold_nm"))
        point_size = bead_size / info.tomo_pixel_size * 10 + 0.5
        self._viewer.set_points(
            mod_data[["z", "y", "x"]].to_numpy(),
            size=point_size,
        )

    def _iter_tomogram_info(self) -> Iterator[_job.TomogramInfo]:
        pipe = self._job_dir.parse_job_pipeline()
        input0 = pipe.get_input_by_type("TomogramGroupMetadata")
        assert input0 is not None, (
            f"No TomogramGroupMetadata input found in {self._job_dir.path}"
        )
        df_tomo = starfile.read(input0.path)
        assert isinstance(df_tomo, pd.DataFrame), type(df_tomo)
        for _, row in df_tomo.iterrows():
            yield _job.TomogramInfo.from_series(row)


class QEraseGoldViewer(QtW.QWidget):
    def __init__(self, job_dir: _job.ExternalJobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = QtW.QVBoxLayout(self)

        self._viewer = Q2DViewer(zlabel="Tilt index")
        self._filter_widget = Q2DFilterWidget()
        self._ts_choice = QtW.QComboBox()
        self._ts_choice.currentTextChanged.connect(self._ts_choice_changed)
        layout.addWidget(QtW.QLabel("<b>Gold-erased tilt series</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._ts_choice)
        layout.addWidget(self._viewer)
        self._filter_widget.value_changed.connect(self._viewer.redraw)
        self._binsize_old = -1
        self.initialize(job_dir)

    def on_job_updated(self, job_dir: _job.ExternalJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".star":
            self._process_update()
            _LOGGER.debug("%s Updated", job_dir.job_id)

    def _param_changed(self):
        """Handle changes to filter parameters."""
        self._viewer.redraw()
        new_binsize = self._filter_widget.bin_factor()
        if self._binsize_old != new_binsize:
            self._binsize_old = new_binsize
            self._viewer.auto_fit()

    def initialize(self, job_dir: _job.ExternalJobDirectory):
        """Initialize the viewer with the job directory."""
        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        choices = [
            p.stem for p in self._job_dir.path.joinpath("tilt_series").glob("*.star")
        ]
        index = self._ts_choice.currentIndex()
        was_empty = self._ts_choice.count() == 0
        self._ts_choice.clear()
        self._ts_choice.addItems(choices)
        if choices:
            self._ts_choice.setCurrentIndex(
                min(index if index >= 0 else 0, len(choices) - 1)
            )
            if was_empty:
                self._viewer.auto_fit()

    def _ts_choice_changed(self, text: str):
        """Update the viewer when the selected tomogram changes."""
        star_path = self._job_dir.path / "tilt_series" / f"{text}.star"
        if not star_path.exists():
            self._viewer.clear()
            self._viewer.redraw()
            return
        df = starfile.read(star_path)
        assert isinstance(df, pd.DataFrame), type(df)
        rln_dir = self._job_dir.relion_project_dir
        paths = [rln_dir / p for p in df["rlnMicrographName"]]
        if "rlnTomoNominalStageTiltAngle" in df:
            tilt_angles = df["rlnTomoNominalStageTiltAngle"]
            order = np.argsort(tilt_angles)
            paths = [paths[i] for i in order]
            df = df.iloc[order].reset_index(drop=True)
        ts_view = ArrayFilteredView.from_mrcs(paths)
        with mrcfile.open(paths[0], header_only=True) as mrc:
            image_scale = mrc.voxel_size.x
        self._filter_widget.set_image_scale(image_scale)
        self._viewer.set_array_view(ts_view.with_filter(self._filter_widget.apply))
