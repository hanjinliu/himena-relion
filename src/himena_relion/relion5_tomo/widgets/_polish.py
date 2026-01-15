from __future__ import annotations

from pathlib import Path
from typing import Iterator
from numpy.typing import NDArray
import logging
import numpy as np
from qtpy import QtWidgets as QtW
from starfile_rs import read_star
from superqt.utils import thread_worker
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DTomogramViewer,
    register_job,
    QMicrographListWidget,
)
from himena_relion import _job_dir
from himena_relion.schemas import OptimisationSetModel, ParticleMetaModel
from himena_relion._image_readers import ArrayFilteredView

_LOGGER = logging.getLogger(__name__)


@register_job("relion.framealigntomo")
class QFrameAlignTomoViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._viewer = Q3DTomogramViewer()
        self._viewer.setMinimumHeight(480)
        self._worker = None
        self._current_info: _job_dir.TomogramInfo | None = None
        self._tomo_list = QMicrographListWidget(["Tomogram"])
        self._tomo_list.current_changed.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Picked tomogram Z slice</b>"))
        layout.addWidget(self._tomo_list)
        layout.addWidget(self._viewer)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix in [".star"]:
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        choices = [(tomo_name,) for tomo_name in self._iter_tomo_names()]
        self._tomo_list.set_choices(choices)
        if len(choices) == 0:
            self._viewer.clear()

    def _on_tomo_changed(self, texts: tuple[str, ...]):
        """Update the viewer when the selected tomogram changes."""
        self.window_closed_callback()
        self._worker = self._read_items(texts[0])
        self._start_worker()

    @thread_worker
    def _read_items(self, text: str):
        # first clear points
        yield self._viewer.set_points, np.empty((0, 3), dtype=np.float32)
        tomo_view = self._get_tomo_view_for_tomo(text)
        if tomo_view is None:
            return self._viewer.clear()
        yield self._set_tomo_view, tomo_view
        ny, nx = tomo_view.get_shape()
        nz = tomo_view.num_slices()
        scale = tomo_view.get_scale()
        center = np.array([(nz - 1) / 2, (ny - 1) / 2, (nx - 1) / 2], dtype=np.float32)
        points = self._get_particles_for_tomo(text)
        points = points / scale + center[np.newaxis]
        yield self._set_points, points
        zoom = 8
        motion = self._get_motions_for_tomo(text, scale, zoom=zoom)
        motion_shifted = [(motion[i] + points[i])[:, ::-1] for i in range(len(motion))]
        yield self._viewer.set_motion_paths, motion_shifted
        self._worker = None

    def _set_tomo_view(self, tomo_view: ArrayFilteredView):
        self._viewer.set_array_view(
            tomo_view,
            self._viewer._last_clim,
            update_now=False,
        )
        self._viewer.auto_fit()

    def _set_points(self, points: NDArray[np.float32]):
        self._viewer.set_points(
            points,
            size=8,
            face_color=[0.8, 0.8, 0, 0.5],
            edge_color=[0, 0, 0, 0.5],
        )

    def _iter_tomo_names(self) -> Iterator[str]:
        tomo_star = self._job_dir.path / "tomograms.star"
        temp_dir = self._job_dir.path / "temp"
        if tomo_star.exists():
            df_tomo = read_star(tomo_star).first().to_polars()
            yield from df_tomo["rlnTomoName"]
        elif temp_dir.exists():
            suffix = "_particles"
            for fp in temp_dir.glob(f"*{suffix}.star"):
                yield fp.stem[: -len(suffix)]

    def _get_motions_for_tomo(
        self,
        tomo_name: str,
        scale: float,
        zoom: float = 1.0,
    ) -> list[np.ndarray]:
        motions = []
        motion_star = self._job_dir.path / "motion.star"
        temp_motion_star = self._job_dir.path / "temp" / f"{tomo_name}_motion.star"
        if temp_motion_star.exists():
            motion_star = temp_motion_star
        elif not motion_star.exists():
            return motions  # nothing available
        for key, block in read_star(motion_star).items():
            # motion data blocks are named as "<tomo_name>/number"
            if key.split("/")[0] != tomo_name:
                continue
            if loop := block.try_loop():
                xyz = loop.to_numpy()  # xyz in A
                motions.append(xyz / scale * zoom)
        return motions

    def _get_particles_for_tomo(self, tomo_name: str) -> NDArray[np.float32]:
        particles_star = self._job_dir.path / "particles.star"
        temp_particles_star = (
            self._job_dir.path / "temp" / f"{tomo_name}_particles.star"
        )
        if temp_particles_star.exists():
            model = ParticleMetaModel.validate_file(temp_particles_star)
            part = model.particles
            z = part.centered_z
            y = part.centered_y
            x = part.centered_x
        elif particles_star.exists():
            model = ParticleMetaModel.validate_file(particles_star)
            part = model.particles
            mask = part.tomo_name == tomo_name
            z = part.centered_z[mask]
            y = part.centered_y[mask]
            x = part.centered_x[mask]
        else:
            return np.empty((0, 3), dtype=np.float32)  # nothing available
        return np.stack([z, y, x], axis=1).astype(np.float32, copy=False)

    def _get_tomo_view_for_tomo(self, tomo_name: str) -> ArrayFilteredView | None:
        params = self._job_dir.get_job_params_as_dict()
        if in_opt := params.get("in_optimisation", ""):
            opt_model = OptimisationSetModel.validate_file(in_opt)
            df_tomo = read_star(opt_model.tomogram_star).first().to_polars()
        elif in_tomo := params.get("in_tomograms", ""):
            df_tomo = read_star(in_tomo).first().to_polars()
        else:
            return None
        if "rlnTomoName" not in df_tomo.columns:
            return None
        sl = df_tomo["rlnTomoName"] == tomo_name
        if "rlnTomoReconstructedTomogramDenoised" in df_tomo.columns:
            path = df_tomo["rlnTomoReconstructedTomogramDenoised"].filter(sl).item()
        elif "rlnTomoReconstructedTomogram" in df_tomo.columns:
            path = df_tomo["rlnTomoReconstructedTomogram"].filter(sl).item()
        else:
            return None
        return ArrayFilteredView.from_mrc(path)
