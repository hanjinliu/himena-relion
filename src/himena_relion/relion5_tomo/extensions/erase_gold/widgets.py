from __future__ import annotations
from pathlib import Path
import logging
from typing import Iterator
import imodmodel
import mrcfile
import pandas as pd
from qtpy import QtWidgets as QtW, QtCore
from starfile_rs import read_star
from himena_relion._image_readers import ArrayFilteredView
from himena_relion._widgets import Q2DViewer, Q2DFilterWidget, QMicrographListWidget
from himena_relion import _job_dir
from himena_relion.schemas import TSModel

_LOGGER = logging.getLogger(__name__)


class QFindBeads3DViewer(QtW.QWidget):
    def __init__(self, job_dir: _job_dir.ExternalJobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = QtW.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self._viewer = Q2DViewer()
        self._viewer.setMaximumHeight(480)
        self._tomo_choice = QMicrographListWidget(["Tomogram", "Fiducials"])
        self._tomo_choice.current_changed.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Tomogram Z slice with fiducials</b>"))
        layout.addWidget(self._tomo_choice)
        layout.addWidget(self._viewer)
        self.initialize(job_dir)

    def on_job_updated(self, job_dir: _job_dir.ExternalJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".mod":
            self._process_update()
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.ExternalJobDirectory):
        """Initialize the viewer with the job directory."""
        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        choices = []
        for info in self._iter_tomogram_info():
            tomo_name = info.tomo_name
            df_mod = self._read_mod(tomo_name)
            if df_mod is None:
                num_fid = "?"
            else:
                num_fid = str(len(df_mod))
            choices.append((tomo_name, num_fid))
        choices.sort(key=lambda x: x[0])
        self._tomo_choice.set_choices(choices)
        if len(choices) == 0:
            self._viewer.clear()

    def _on_tomo_changed(self, texts: tuple[str, ...]):
        """Update the viewer when the selected tomogram changes."""
        text = texts[0]  # tomo name
        for info in self._iter_tomogram_info():
            if info.tomo_name == text:
                break
        else:
            return
        df_mod = self._read_mod(text)
        if df_mod is None:
            self._viewer.clear()
            return
        tomo_view = info.read_tomogram(self._job_dir.relion_project_dir)
        self._viewer.set_array_view(tomo_view, self._viewer._last_clim)
        bead_size = float(self._job_dir.get_job_param("gold_nm"))
        point_size = bead_size / info.tomo_pixel_size * 10 + 0.5
        self._viewer.set_points(df_mod[["z", "y", "x"]].to_numpy(), size=point_size)

    def _iter_tomogram_info(self) -> Iterator[_job_dir.TomogramInfo]:
        pipe = self._job_dir.parse_job_pipeline()
        input0 = pipe.get_input_by_type("MicrographGroupMetadata")
        if input0 is None:
            input0 = pipe.get_input_by_type("TomogramGroupMetadata")
        if input0 is None:
            raise ValueError(
                f"No TomogramGroupMetadata input found in {self._job_dir.path}"
            )
        df_tomo = read_star(input0.path).first().trust_loop().to_pandas()
        for _, row in df_tomo.iterrows():
            yield _job_dir.TomogramInfo.from_series(row)

    def _read_mod(self, tomo_name: str) -> pd.DataFrame | None:
        mod_path = self._job_dir.path / "models" / f"{tomo_name}.mod"
        if mod_path.exists():
            return imodmodel.read(mod_path)


class QEraseGoldViewer(QtW.QWidget):
    def __init__(self, job_dir: _job_dir.ExternalJobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = QtW.QVBoxLayout(self)

        self._viewer = Q2DViewer(zlabel="Tilt index")
        self._filter_widget = Q2DFilterWidget(bin_default=8, lowpass_default=30)
        self._ts_choice = QMicrographListWidget(["Tilt Series"])
        self._ts_choice.current_changed.connect(self._ts_choice_changed)
        layout.addWidget(QtW.QLabel("<b>Gold-erased tilt series</b>"))
        layout.addWidget(self._ts_choice)
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._viewer)
        self._filter_widget.value_changed.connect(self._viewer.redraw)
        self._binsize_old = -1
        self.initialize(job_dir)

    def on_job_updated(self, job_dir: _job_dir.ExternalJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix == ".star":
            self._process_update()
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def _param_changed(self):
        """Handle changes to filter parameters."""
        self._viewer.redraw()
        new_binsize = self._filter_widget.bin_factor()
        if self._binsize_old != new_binsize:
            self._binsize_old = new_binsize
            self._viewer.auto_fit()

    def initialize(self, job_dir: _job_dir.ExternalJobDirectory):
        """Initialize the viewer with the job directory."""
        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        ts_dir = self._job_dir.path.joinpath("tilt_series")
        choices = [(p.stem,) for p in ts_dir.glob("*.star")]
        choices.sort()
        self._ts_choice.set_choices(choices)
        if len(choices) == 0:
            self._viewer.clear()

    def _ts_choice_changed(self, texts: tuple[str, ...]):
        """Update the viewer when the selected tomogram changes."""
        text = texts[0]  # tomo name
        star_path = self._job_dir.path / "tilt_series" / f"{text}.star"
        if not star_path.exists():
            self._viewer.clear()
            return
        ts = TSModel.validate_file(star_path)
        rln_dir = self._job_dir.relion_project_dir
        paths = ts.ts_paths_sorted(rln_dir)
        ts_view = ArrayFilteredView.from_mrcs(paths)
        with mrcfile.open(paths[0], header_only=True) as mrc:
            image_scale = mrc.voxel_size.x
        self._filter_widget.set_image_scale(image_scale)
        self._viewer.set_array_view(ts_view.with_filter(self._filter_widget.apply))
