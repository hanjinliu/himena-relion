from __future__ import annotations
from typing import Callable, Iterator
from pathlib import Path
import logging
from contextlib import suppress

from qtpy import QtWidgets as QtW
import pandas as pd
import numpy as np
from starfile_rs import read_star
from superqt.utils import thread_worker, GeneratorWorker
from himena_relion._widgets import Q2DViewer, Q2DFilterWidget
from himena_relion import _job_dir
from himena_relion.schemas import OptimisationSetModel, ParticleMetaModel

_LOGGER = logging.getLogger(__name__)


class QInspectViewer(QtW.QWidget):
    def __init__(self, job_dir: _job_dir.ExternalJobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = QtW.QVBoxLayout(self)

        self._viewer = Q2DViewer()
        self._worker: GeneratorWorker | None = None
        self._current_info: _job_dir.TomogramInfo | None = None
        self._filter_widget = Q2DFilterWidget()
        self._filter_widget._bin_factor.setText("1")
        self._tomo_choice = QtW.QComboBox()
        self._tomo_choice.currentTextChanged.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Picked tomogram Z slice</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._tomo_choice)
        layout.addWidget(self._viewer)
        self._filter_widget.value_changed.connect(self._viewer.redraw)
        self.initialize(job_dir)

    def on_job_updated(self, job_dir: _job_dir.ExternalJobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.name == "optimisation_set.star":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_id)

    def initialize(self, job_dir: _job_dir.ExternalJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        current_text = self._tomo_choice.currentText()
        items = [info.tomo_name for info in _iter_tomograms(job_dir)]
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
        job_dir = self._job_dir
        if job_dir is None:
            return
        for info in _iter_tomograms(job_dir):
            if info.tomo_name == text:
                break
        else:
            return
        if self._worker is not None and self._worker.is_running:
            self._worker.quit()
            self._worker = None
        tomo_view = info.read_tomogram(job_dir.relion_project_dir)
        self._viewer.set_points(
            np.empty((0, 3), dtype=np.float32)
        )  # first clear points
        self._viewer.set_array_view(tomo_view, self._viewer._last_clim)
        if getter := info.get_particles:
            self._current_info = info
            worker = thread_worker(getter)()
            self._worker = worker
            worker.returned.connect(self._on_worker_returned)
            worker.start()

    def _on_worker_returned(self, point_df: pd.DataFrame):
        self._worker = None
        with suppress(RuntimeError):
            info = self._current_info
            if info is None:
                return
            cols = [f"rlnCenteredCoordinate{x}Angst" for x in "ZYX"]
            points = point_df[cols].to_numpy(dtype=np.float32) / info.tomo_pixel_size
            sizes = np.array(info.tomo_shape, dtype=np.float32) / info.tomogram_binning
            center = (sizes - 1) / 2
            self._viewer.set_points(points + center[np.newaxis])
            self._viewer.redraw()


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
            sl = ptcl.tomo_name == tomo_name
            return ptcl.dataframe[sl].reset_index(drop=True)

    return get_particles
