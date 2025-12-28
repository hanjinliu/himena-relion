from __future__ import annotations
from pathlib import Path
import logging
from typing import Iterator
import numpy as np
from starfile_rs import read_star
from qtpy import QtWidgets as QtW
from himena_relion._image_readers._array import ArrayFilteredView
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    Q2DFilterWidget,
    register_job,
)
from himena_relion import _job_dir
from ._shared import QMicrographListWidget

_LOGGER = logging.getLogger(__name__)


@register_job("relion.manualpick")
class QManualPickViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._viewer = Q2DViewer(zlabel="")
        self._mic_list = QMicrographListWidget(["Micrograph", "Picked", "Coordinates"])
        self._mic_list.setFixedHeight(130)
        self._mic_list.setColumnHidden(2, True)
        self._mic_list.current_changed.connect(self._mic_changed)
        self._filter_widget = Q2DFilterWidget()
        layout.addWidget(QtW.QLabel("<b>Micrographs with picked particles</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._viewer)
        layout.addWidget(self._mic_list)
        self._filter_widget.value_changed.connect(self._filter_param_changed)
        self._binsize_old = -1

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".star":
            self._process_update()
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def _mic_changed(self, row: tuple[str, str, str]):
        """Handle changes to selected micrograph."""
        rln_dir = self._job_dir.relion_project_dir
        mic_path = rln_dir / row[0]
        df_coords = read_star(rln_dir / row[2]).first().trust_loop().to_pandas()
        movie_view = ArrayFilteredView.from_mrc(mic_path)
        had_image = self._viewer.has_image
        self._filter_widget.set_image_scale(movie_view.get_scale())
        self._viewer.set_array_view(
            movie_view.with_filter(self._filter_widget.apply),
            clim=self._viewer._last_clim,
        )

        arr = df_coords[["rlnCoordinateY", "rlnCoordinateX"]].to_numpy()
        arr = np.column_stack((np.zeros(arr.shape[0], dtype=arr.dtype), arr))
        # TODO: use correct size
        self._viewer.set_points(
            arr,
            size=10,
        )
        if not had_image:
            self._viewer._auto_contrast()

    def _filter_param_changed(self):
        """Handle changes to filter parameters."""
        self._viewer.redraw()
        new_binsize = self._filter_widget.bin_factor()
        if self._binsize_old != new_binsize:
            self._binsize_old = new_binsize
            self._viewer.auto_fit()

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir

        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        choices = []
        for mic_path, coords_path in iter_micrograph_and_coordinates(self._job_dir):
            num = read_star(coords_path).first().trust_loop().shape[0]
            choices.append((mic_path, str(num), coords_path))
        self._mic_list.set_choices(choices)


def iter_micrograph_and_coordinates(
    job_dir: _job_dir.JobDirectory,
) -> Iterator[tuple[str, str]]:
    star_path = job_dir.path / "manualpick.star"
    if star_path.exists():
        df = read_star(star_path).first().trust_loop().to_pandas()
        for _, row in df.iterrows():
            full_path, coord_path, *_ = row
            yield full_path, coord_path


def iter_local_selection(job_dir: _job_dir.JobDirectory) -> Iterator[tuple]:
    # micrograph path, picked number, is selected, full path
    local_selection_path = job_dir.path / "local_selection.star"
    if local_selection_path.exists():
        df = read_star(local_selection_path).first().trust_loop().to_pandas()
        for _, row in df.iterrows():
            full_path, is_selected, *_ = row
            full_path = Path(full_path)
            name = full_path.name
            job_dir.path / "Movies" / f"{full_path.stem}_manualpick.star"
            yield name, 0, bool(is_selected), str(full_path)
