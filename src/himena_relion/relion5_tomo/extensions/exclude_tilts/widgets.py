from __future__ import annotations

from starfile_rs import read_star
from himena_relion import _job_dir
from himena_relion.relion5_tomo.widgets._tilt_series import (
    QExcludeTiltsWidget,
    EXCLUDED_TILTS_STAR,
)


class QAutoExcludeTiltsViewer(QExcludeTiltsWidget):
    def __init__(self, job_dir: _job_dir.ExternalJobDirectory):
        super().__init__(job_dir, list_auto_excluded)
        self.layout().setContentsMargins(2, 2, 2, 2)


def list_auto_excluded(job_dir: _job_dir.JobDirectory) -> list[str]:
    """List micrographs recorded in `excluded_tilts.star`."""
    star_path = job_dir.path / EXCLUDED_TILTS_STAR
    if not star_path.exists():
        return []
    df = read_star(star_path).first().trust_loop().to_polars()
    if df.height == 0 or "rlnMicrographName" not in df.columns:
        return []
    return df["rlnMicrographName"].to_list()
