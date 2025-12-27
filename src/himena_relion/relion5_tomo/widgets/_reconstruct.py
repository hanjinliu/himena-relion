from __future__ import annotations
from pathlib import Path
import logging

from qtpy.QtCore import Qt
from starfile_rs import read_star
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    spacer_widget,
)
from himena_relion import _job_dir
from himena_relion.schemas import OptimisationSetModel
from ._shared import QNumParticlesLabel

_LOGGER = logging.getLogger(__name__)


@register_job(_job_dir.ReconstructParticlesJobDirectory)
class QReconstructViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._viewer = Q3DViewer()
        self._num_particles_label = QNumParticlesLabel()
        self._num_particles_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._num_particles_label.setMaximumWidth(self._viewer.maximumWidth())
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(self._num_particles_label)
        self._layout.addWidget(spacer_widget())

    def on_job_updated(
        self, job_dir: _job_dir.ReconstructParticlesJobDirectory, path: str
    ):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_id)

    def initialize(self, job_dir: _job_dir.ReconstructParticlesJobDirectory):
        """Initialize the viewer with the job directory."""
        img = job_dir.merged_mrc()
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
                particles_path = ptcl
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
