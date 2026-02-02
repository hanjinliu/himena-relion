from __future__ import annotations
from typing import Callable, Iterator
from pathlib import Path
import logging

from qtpy import QtWidgets as QtW
import pandas as pd
import numpy as np
from starfile_rs import read_star
from superqt.utils import thread_worker, GeneratorWorker
from himena_relion._image_readers import ArrayFilteredView
from himena_relion._widgets import (
    Q3DTomogramViewer,
    Q2DFilterWidget,
    QMicrographListWidget,
)
from himena_relion import _job_dir
from himena_relion.schemas import OptimisationSetModel, ParticleMetaModel

_LOGGER = logging.getLogger(__name__)


class QInspectViewer(QtW.QWidget):
    def __init__(self, job_dir: _job_dir.ExternalJobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = QtW.QVBoxLayout(self)

        self._viewer = Q3DTomogramViewer()
        self._worker: GeneratorWorker | None = None
        self._current_info: _job_dir.TomogramInfo | None = None
        self._filter_widget = Q2DFilterWidget()
        self._filter_widget._bin_factor.setText("1")
        self._tomo_choice = QMicrographListWidget(["Tomogram"])
        self._tomo_choice.current_changed.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Picked tomogram Z slice</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._tomo_choice)
        layout.addWidget(self._viewer)
        # self._filter_widget.value_changed.connect(self._viewer.redraw)
        self.initialize(job_dir)

    def on_job_updated(self, job_dir: _job_dir.ExternalJobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.name == "optimisation_set.star":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.ExternalJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        choices = [(info.tomo_name,) for info in _iter_tomograms(job_dir)]
        choices.sort(key=lambda x: x[0])
        self._tomo_choice.set_choices(choices)
        if len(choices) == 0:
            self._viewer.clear()
        else:
            self._viewer.auto_fit()

    def _on_tomo_changed(self, texts: tuple[str, ...]):
        """Update the viewer when the selected tomogram changes."""
        if self._worker is not None and self._worker.is_running:
            self._worker.quit()
            self._worker = None
        self._worker = self._read_items(texts[0])
        self._worker.start()

    @thread_worker
    def _read_items(self, text: str):
        # first clear points
        yield self._viewer.set_points, np.empty((0, 3), dtype=np.float32)
        for info in _iter_tomograms(self._job_dir):
            if info.tomo_name == text:
                break
        else:
            return
        tomo_view = info.read_tomogram(self._job_dir.relion_project_dir)
        self._filter_widget.set_image_scale(info.tomo_pixel_size)
        yield self._set_tomo_view, tomo_view.with_filter(self._filter_widget.apply)
        if getter := info.get_particles:
            point_df = getter()
            cols = [f"rlnCenteredCoordinate{x}Angst" for x in "ZYX"]
            points = point_df[cols].to_numpy(dtype=np.float32) / info.tomo_pixel_size
            sizes = np.array(info.tomo_shape, dtype=np.float32) / info.tomogram_binning
            center = (sizes - 1) / 2
            bin_factor = int(self._filter_widget._bin_factor.text() or "1")
            points_processed = (points + center[np.newaxis]) / bin_factor
            yield self._viewer.set_points, points_processed
        self._worker = None

    def _set_tomo_view(self, tomo_view: ArrayFilteredView):
        self._viewer.set_array_view(
            tomo_view,
            self._viewer._last_clim,
            update_now=False,
        )
        self._viewer.auto_fit()

    def _on_yielded(self, yielded):
        fn, args = yielded
        fn(args)


def _tomo_and_particles_star(
    job: _job_dir.ExternalJobDirectory,
) -> tuple[Path | None, Path | None]:
    """Return the path to the tomogram and particles star file."""
    try:
        job_pipeline = job.parse_job_pipeline()
    except FileNotFoundError:
        return None, None
    rln_dir = job.relion_project_dir
    if node := job_pipeline.get_input_by_type("MicrographGroupMetadata"):
        tomo_star_path = rln_dir / node.path
    else:
        tomo_star_path = None
    if (path_opt := job.path / "optimisation_set.star").exists():
        opt_set = OptimisationSetModel.validate_file(path_opt)
        particle_star_path = rln_dir / opt_set.particles_star
    elif node_part := job_pipeline.get_input_by_type("ParticleGroupMetadata"):
        particle_star_path = rln_dir / node_part.path
    else:
        particle_star_path = None
    return tomo_star_path, particle_star_path


def _iter_tomograms(
    job: _job_dir.ExternalJobDirectory,
) -> Iterator[_job_dir.TomogramInfo]:
    """Iterate over all tilt series info."""
    tomo_star, particles_star = _tomo_and_particles_star(job)
    if tomo_star is None:
        return
    star = read_star(tomo_star).first().trust_loop().to_pandas()
    for _, row in star.iterrows():
        info = _job_dir.TomogramInfo.from_series(row)
        getter = _make_get_particles(particles_star, info.tomo_name)
        info.get_particles = getter
        yield info


def _make_get_particles(
    particles_star: Path,
    tomo_name: str,
) -> Callable[[], pd.DataFrame]:
    """Create a function to get particles for a given tomogram."""

    def get_particles() -> pd.DataFrame:
        if particles_star is None:
            cols = [f"rlnCenteredCoordinate{x}Angst" for x in "ZYX"]
            return pd.DataFrame({c: [] for c in cols}, dtype=float)
        else:
            ptcl = ParticleMetaModel.validate_file(particles_star)
            sl = ptcl.particles.tomo_name == tomo_name
            return ptcl.particles.dataframe[sl].reset_index(drop=True)

    return get_particles
