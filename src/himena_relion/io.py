from __future__ import annotations

from pathlib import Path
from himena import WidgetDataModel
from himena.plugins import register_reader_plugin
from himena_relion.consts import Type


@register_reader_plugin(priority=500)
def read_relion_job(path: Path) -> WidgetDataModel:
    if job_star := _get_job_star(path):
        from himena_relion import _job

        job_dir = _job.Refine3DJobDirectory.from_job_star(job_star)
        return WidgetDataModel(value=job_dir, type=Type.RELION_JOB)
    raise ValueError(f"Expected an existing job.star file, got {path}")


@read_relion_job.define_matcher
def _(path: Path):
    if _get_job_star(path) is not None:
        return Type.RELION_JOB
    return None


def _get_job_star(path: Path) -> Path | None:
    """Get the path to the job.star file."""
    if path.is_dir() and (job_star := path.joinpath("job.star")).exists():
        return job_star
    if path.is_file() and path.name == "job.star":
        return path
    return None
