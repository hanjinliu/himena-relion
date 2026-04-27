from __future__ import annotations

from pathlib import Path
from himena_relion._widgets._shared.picking import QMicrographParticleOverlay


class TakeZeroTiltMicrographsWidget(QMicrographParticleOverlay):
    """Take zero-tilt micrographs and particles from tomogram for SPA."""

    def _get_particles_star(self) -> Path:
        return self._job_dir.path / "hybrid_data.star"
