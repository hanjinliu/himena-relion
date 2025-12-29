from __future__ import annotations
from pathlib import Path
import logging
from typing import Iterator
import mrcfile
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
from himena_relion.schemas import MicCoordSetModel, CoordsModel
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
        self._coords: CoordsModel | None = None

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
        movie_view = ArrayFilteredView.from_mrc(mic_path)
        had_image = self._viewer.has_image
        image_scale = movie_view.get_scale()
        self._filter_widget.set_image_scale(image_scale)
        self._viewer.set_array_view(
            movie_view.with_filter(self._filter_widget.apply),
            clim=self._viewer._last_clim,
        )
        self._coords = CoordsModel.validate_file(rln_dir / row[2])

        self._update_points()
        if not had_image:
            self._viewer._auto_contrast()

    def _filter_param_changed(self):
        """Handle changes to filter parameters."""
        self._viewer.redraw()
        new_binsize = self._filter_widget.bin_factor()
        if self._binsize_old != new_binsize:
            self._binsize_old = new_binsize
            self._viewer.auto_fit()
        self._update_points()

    def _update_points(self):
        if self._coords is None:
            return
        arr = np.column_stack(
            [np.zeros(len(self._coords.x)), self._coords.y, self._coords.x]
        )
        image_scale = self._filter_widget._image_scale
        bins = self._filter_widget.bin_factor()
        try:
            diameter = self._get_diameter()
        except Exception:
            diameter = 50.0
        self._viewer.set_points(arr / bins, size=diameter / image_scale / bins)
        self._viewer.redraw()

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

    def _get_diameter(self) -> float:
        return float(self._job_dir.get_job_param("diameter"))


def iter_micrograph_and_coordinates(
    job_dir: _job_dir.JobDirectory,
    filename: str = "manualpick.star",
) -> Iterator[tuple[str, str]]:
    star_path = job_dir.path / filename
    if star_path.exists():
        model = MicCoordSetModel.validate_file(star_path)
        for full_path, coord_path in zip(model.micrographs, model.coords):
            yield (
                job_dir.resolve_path(full_path).as_posix(),
                job_dir.resolve_path(coord_path).as_posix(),
            )


class QAutopickViewerBase(QManualPickViewer):
    """Viewer for template-based autopicking jobs."""

    def _process_update(self):
        choices = []
        for mic_path, coords_path in iter_micrograph_and_coordinates(
            self._job_dir, "autopick.star"
        ):
            num = read_star(coords_path).first().trust_loop().shape[0]
            choices.append((mic_path, str(num), coords_path))
        self._mic_list.set_choices(choices)


# fallback for relion.autopick
@register_job("relion.autopick.ref2d")
@register_job("relion.autopick")
class QTemplatePick2DViewer(QAutopickViewerBase):
    def _get_diameter(self) -> float:
        return 50.0


@register_job("relion.autopick.ref3d")
class QTemplatePick3DViewer(QAutopickViewerBase):
    def _get_diameter(self) -> float:
        path = self._job_dir.path / "reference_projections.mrcs"
        with mrcfile.open(path, header_only=True) as mrc:
            return float(mrc.voxel_size.x)


@register_job("relion.autopick.log")
class QLoGPickViewer(QAutopickViewerBase):
    def _get_diameter(self) -> float:
        return float(self._job_dir.get_job_param("log_diam_max"))
