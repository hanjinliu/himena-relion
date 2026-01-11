from __future__ import annotations
from pathlib import Path
import logging

import mrcfile
import numpy as np
from qtpy.QtCore import Qt
from starfile_rs import read_star
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    QNumParticlesLabel,
)
from himena_relion import _job_dir
from himena_relion.schemas import OptimisationSetModel

_LOGGER = logging.getLogger(__name__)


@register_job("relion.reconstructparticletomo", is_tomo=True)
class QReconstructViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._viewer = Q3DViewer()
        self._viewer.setMaximumWidth(400)
        self._num_particles_label = QNumParticlesLabel()
        self._num_particles_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._num_particles_label.setMaximumWidth(self._viewer.maximumWidth())
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(self._num_particles_label)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        img = merged_mrc(job_dir)
        self._viewer.set_image(img, update_now=False)
        self._viewer.auto_threshold(update_now=False)
        self._viewer.auto_fit()

        # get the number of particles
        try:
            params = job_dir.get_job_params_as_dict()
            if opt_path := params.get("in_optimisation", None):
                opt_path = job_dir.relion_project_dir / opt_path
                opt_model = OptimisationSetModel.validate_file(opt_path)
                particles_path = opt_model.particles_star
            elif ptcl := params.get("in_particles", None):
                particles_path = job_dir.resolve_path(ptcl)
            else:
                return
            if not particles_path.exists():
                particles_path = job_dir.relion_project_dir / particles_path
            star = read_star(particles_path)
            if "particles" in star:
                n_particles = star["particles"].trust_loop().shape[0]
            elif len(star) == 1:
                n_particles = star.first().trust_loop().shape[0]
            else:
                n_particles = -1
        except Exception:
            n_particles = -1
            _LOGGER.warning(
                "Failed to read particles star file to get number of particles",
                exc_info=True,
            )
        self._num_particles_label.set_number(n_particles)


def merged_mrc(job_dir: _job_dir.JobDirectory) -> np.ndarray | None:
    """Return the path to the merged MRC file if exists."""
    path = job_dir.path / "merged.mrc"
    try:
        with mrcfile.open(path, mode="r") as mrc:
            return mrc.data
    except Exception:
        return None
