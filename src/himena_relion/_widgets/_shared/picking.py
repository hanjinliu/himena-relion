from __future__ import annotations

from pathlib import Path
import numpy as np
from qtpy import QtWidgets as QtW
from starfile_rs import read_star
from himena.qt.magicgui import ToggleSwitch
from himena_relion import _job_dir
from himena_relion._image_readers._array import ArrayFilteredView
from himena_relion._widgets import (
    Q2DViewer,
    Q2DFilterWidget,
    QMicrographListWidget,
)
from himena_relion._widgets._misc import spacer_widget
from himena_relion._widgets._shared.resizer import QResizer
from himena_relion.schemas import CoordsModel, MicrographsStarModel


class QMicrographParticleOverlay(QtW.QWidget):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir

        self._viewer = Q2DViewer(zlabel="")
        self._viewer.setMinimumHeight(480)
        self._resizer = QResizer(self._viewer)
        self._mic_list = QMicrographListWidget(["Micrograph", "Micrograph Full Path"])
        self._mic_list.setFixedHeight(130)
        self._mic_list.setColumnHidden(2, True)
        self._mic_list.setColumnHidden(3, True)
        self._mic_list.current_changed.connect(self._mic_changed)
        self._filter_widget = Q2DFilterWidget(bin_default=8, lowpass_default=20)
        self._filter_widget.value_changed.connect(self._filter_param_changed)
        self._show_points_switch = ToggleSwitch(text="Show Particles", value=True)
        self._show_points_switch.changed.connect(self._set_marker_visible)
        self._binsize_old = -1
        self._current_particles: CoordsModel | None = None

        layout = QtW.QVBoxLayout(self)
        header = QtW.QHBoxLayout()
        header.addWidget(self._filter_widget)
        header.addWidget(self._show_points_switch.native)
        layout.addLayout(header)
        layout.addWidget(self._viewer)
        layout.addWidget(self._resizer)
        layout.addWidget(self._mic_list)
        layout.addWidget(spacer_widget())
        self.initialize(job_dir)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        self._viewer.clear()
        if (mic_path := self._get_micrograph_star()).exists():
            mic_model = MicrographsStarModel.validate_file(mic_path)
            entries = []
            for mpath in mic_model.micrographs.mic_name:
                entries.append((Path(mpath).name, mpath))
            self._mic_list.set_choices(entries)
        if (particles_path := self._get_particles_star()).exists():
            star = read_star(particles_path)
            if _particles_block := star.get("particles"):
                self._current_particles = CoordsModel.validate_object(_particles_block)
            elif len(star) == 1:
                self._current_particles = CoordsModel.validate_object(star.first())
            else:
                raise ValueError("STAR file is not an SPA particle file.")
        self._mic_changed(self._mic_list.current_row_texts())
        self._viewer.auto_fit()

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name == self._get_particles_star().name:
            self.initialize(job_dir)

    def _get_micrograph_star(self) -> Path:
        return self._job_dir.path / "micrographs.star"

    def _get_particles_star(self) -> Path:
        return self._job_dir.path / "particles.star"

    def _mic_changed(self, row: tuple[str, str] | None):
        """Handle changes to selected micrograph."""
        if row is None:
            self._viewer.clear()
            return
        _, _mic_path = row
        mic_path = self._job_dir.resolve_path(_mic_path)
        mic_view = ArrayFilteredView.from_mrc(mic_path)
        image_scale = mic_view.get_scale()
        self._filter_widget.set_image_scale(image_scale)
        self._viewer.set_array_view(
            mic_view.with_filter(self._filter_widget.apply),
            clim=self._viewer._last_clim,
        )
        self._reload_coords(_mic_path)
        self._viewer._auto_contrast()

    def _filter_param_changed(self):
        """Handle changes to filter parameters."""
        self._viewer.redraw()
        new_binsize = self._filter_widget.bin_factor()
        if self._binsize_old != new_binsize:
            self._binsize_old = new_binsize
            self._viewer.auto_fit()
        if texts := self._mic_list.current_row_texts():
            self._reload_coords(texts[1])

    def _reload_coords(self, mic_path: str):
        if self._current_particles is None:
            return
        is_match = self._current_particles.mic_name == mic_path
        scale = self._filter_widget.image_scale()
        # TODO: orig need to be rotated.
        if self._current_particles.orig_x is not None:
            dx = self._current_particles.orig_x.filter(is_match) / scale
        else:
            dx = 0
        if self._current_particles.orig_y is not None:
            dy = self._current_particles.orig_y.filter(is_match) / scale
        else:
            dy = 0
        x = self._current_particles.x.filter(is_match) + dx
        y = self._current_particles.y.filter(is_match) + dy
        arr = np.stack([np.zeros(y.len()), y.to_numpy(), x.to_numpy()], axis=1)
        bins = self._filter_widget.bin_factor()
        diameter = 200
        self._viewer.set_points(arr / bins, size=diameter / scale / bins)
        self._viewer.redraw()

    def _clear_points(self, *_):
        """Clear all the points before reloading."""
        self._viewer.set_points(np.empty((0, 3)))
        self._viewer.redraw()

    def _set_marker_visible(self, visible: bool):
        """Set the visibility of the points."""
        self._viewer._canvas.markers_visual.visible = visible
        self._viewer._canvas.update_canvas()
