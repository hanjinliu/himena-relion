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
    QImageViewTextEdit,
    QMicrographListWidget,
)
from himena_relion import _job_dir
from himena_relion.relion5._connections import _get_template_last_iter
from himena_relion.schemas import CoordsModel, MicrographGroupMetaModel

_LOGGER = logging.getLogger(__name__)


@register_job("relion.manualpick")
class QManualPickViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._viewer = Q2DViewer(zlabel="")
        self._last_update: dict[str, tuple[float, int]] = {}  # path -> (mtime, npoints)
        self._viewer.setMinimumSize(300, 330)
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
        if fp.name.startswith("RELION_JOB_") or fp.suffix in (".star", ".mrcs"):
            self._process_update()
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def _mic_changed(self, row: tuple[str, str, str]):
        """Handle changes to selected micrograph."""
        _mic_path, _, _coords_path = row
        mic_path = self._job_dir.resolve_path(_mic_path)
        movie_view = ArrayFilteredView.from_mrc(mic_path)
        image_scale = movie_view.get_scale()
        self._filter_widget.set_image_scale(image_scale)
        self._viewer.set_array_view(
            movie_view.with_filter(self._filter_widget.apply),
            clim=self._viewer._last_clim,
        )
        self._update_points(reload=_coords_path)
        self._viewer._auto_contrast()

    def _filter_param_changed(self):
        """Handle changes to filter parameters."""
        self._viewer.redraw()
        new_binsize = self._filter_widget.bin_factor()
        if self._binsize_old != new_binsize:
            self._binsize_old = new_binsize
            self._viewer.auto_fit()
        self._update_points()

    def _update_points(self, reload: str = ""):
        if reload and (coords_path := self._job_dir.resolve_path(reload)).exists():
            self._coords = CoordsModel.validate_file(coords_path)
        else:
            self._coords = None

        if self._coords is None:
            self._viewer.set_points(np.empty((0, 3)))
        else:
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
        self._viewer.clear()
        self._last_update.clear()
        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        choices = []
        for mic_path, coords_path in iter_micrograph_and_coordinates(self._job_dir):
            if coords_path is None:
                num = 0
            else:
                coords_path = self._job_dir.resolve_path(coords_path)
                if not coords_path.exists():
                    num = 0
                    self._last_update.pop(coords_path.stem, None)
                else:
                    # reading all the particles can be slow, so use mtime caching
                    mtime0, num0 = self._last_update.get(coords_path.stem, (-1, 0))
                    if (mtime := coords_path.stat().st_mtime) <= mtime0:
                        num = num0
                    else:
                        num = read_star(coords_path).first().trust_loop().shape[0]
                        self._last_update[coords_path.stem] = mtime, num
                coords_path = coords_path.as_posix()
            choices.append((mic_path, str(num), coords_path or ""))
        self._mic_list.set_choices(choices)
        self._update_points(reload=self._mic_list.current_text(2))

    def _get_diameter(self) -> float:
        return float(self._job_dir.get_job_param("diameter"))


def iter_micrograph_and_coordinates(
    job_dir: _job_dir.JobDirectory,
) -> Iterator[tuple[str, str | None]]:
    pipeline = job_dir.parse_job_pipeline()
    mic = pipeline.get_input_by_type("MicrographGroupMetadata")
    if mic is None:
        return
    mic_model = MicrographGroupMetaModel.validate_file(job_dir.resolve_path(mic.path))
    movie_dir = job_dir.path / "Movies"
    for path in mic_model.micrographs.mic_name:
        stem = Path(path).stem
        if (pickpath := movie_dir.joinpath(stem + "_autopick.star")).exists():
            pick_star = job_dir.make_relative_path(pickpath).as_posix()
        elif (pickpath := movie_dir.joinpath(stem + "_manualpick.star")).exists():
            pick_star = job_dir.make_relative_path(pickpath).as_posix()
        else:
            pick_star = None
        yield (path, pick_star)


class QAutopickViewerBase(QManualPickViewer):
    """Viewer for template-based autopicking jobs."""


# fallback for relion.autopick
@register_job("relion.autopick")
class QAutoViewer(QAutopickViewerBase):
    def _get_diameter(self) -> float:
        return 50.0


@register_job("relion.autopick.ref2d")
class QTemplatePick2DViewer(QAutopickViewerBase):
    def _get_diameter(self) -> float:
        path = self._job_dir.resolve_path(_get_template_last_iter(self._job_dir.path))
        with mrcfile.open(path, header_only=True) as mrc:
            return float(mrc.voxel_size.x * mrc.header.nx)


@register_job("relion.autopick.ref3d")
class QTemplatePick3DViewer(QAutopickViewerBase):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__(job_dir)
        self._text_edit = QImageViewTextEdit(image_size_pixel=64)
        self._text_edit.setMinimumHeight(120)
        self._layout.insertWidget(0, QtW.QLabel("<b>Reference Projections</b>"))
        self._layout.insertWidget(1, self._text_edit)
        self._last_ref_proj_mtime: float = 0.0

    def _get_diameter(self) -> float:
        path = self._job_dir.path / "reference_projections.mrcs"
        with mrcfile.open(path, header_only=True) as mrc:
            return float(mrc.voxel_size.x * mrc.header.nx)

    def _process_update(self):
        super()._process_update()
        ref_proj_path = self._job_dir.path / "reference_projections.mrcs"
        if ref_proj_path.exists():
            if (mtime := ref_proj_path.stat().st_mtime) <= self._last_ref_proj_mtime:
                return
            self._last_ref_proj_mtime = mtime
            self._text_edit.clear()
            with mrcfile.open(ref_proj_path) as mrc:
                images = np.asarray(mrc.data, dtype=np.float32)
            for img_slice in images:
                img_str = self._text_edit.image_to_base64(img_slice)
                self._text_edit.insert_base64_image(img_str)


@register_job("relion.autopick.log")
class QLoGPickViewer(QAutopickViewerBase):
    def _get_diameter(self) -> float:
        return float(self._job_dir.get_job_param("log_diam_max"))
