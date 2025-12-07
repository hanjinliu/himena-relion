from __future__ import annotations

from pathlib import Path
import numpy as np
from himena import StandardType, WidgetDataModel, create_image_model
from himena.standards.model_meta import DimAxis
from himena.plugins import register_reader_plugin
from himena_relion.consts import Type


@register_reader_plugin(priority=0)
def read_density_map(path: Path) -> WidgetDataModel:
    import mrcfile

    with mrcfile.open(path, permissive=True) as mrc:
        arr = np.asarray(mrc.data)
        voxel_size = mrc.voxel_size
    axes = [
        DimAxis(name="z", scale=voxel_size.z, unit="Å"),
        DimAxis(name="y", scale=voxel_size.y, unit="Å"),
        DimAxis(name="x", scale=voxel_size.x, unit="Å"),
    ]
    return create_image_model(
        arr,
        axes=axes,
        extension_default=".mrc",
        force_open_with="himena-relion:Q3DViewer",
    )


@read_density_map.define_matcher
def _(path: Path):
    return StandardType.IMAGE


@register_reader_plugin(priority=500)
def read_relion_job(path: Path) -> WidgetDataModel:
    if job_star := _get_job_star(path):
        from himena_relion import _job

        job_dir = _job.JobDirectory.from_job_star(job_star)
        return WidgetDataModel(value=job_dir, type=Type.RELION_JOB)
    raise ValueError(f"Expected an existing job.star file, got {path}")


@read_relion_job.define_matcher
def _(path: Path):
    if _get_job_star(path) is not None:
        return Type.RELION_JOB
    return None


@register_reader_plugin(priority=500)
def read_relion_pipeline(path: Path) -> WidgetDataModel:
    if pipeline_star := _get_default_pipeline_star(path):
        from himena_relion import _pipeline

        pipeline = _pipeline.RelionPipeline.from_pipeline_star(pipeline_star)
        return WidgetDataModel(value=pipeline, type=Type.RELION_PIPELINE)


@read_relion_pipeline.define_matcher
def _(path: Path):
    if _get_default_pipeline_star(path) is not None:
        return Type.RELION_PIPELINE
    return None


def _get_job_star(path: Path) -> Path | None:
    """Get the path to the job.star file."""
    return _get_star(path, "job.star")


def _get_default_pipeline_star(path: Path) -> Path | None:
    """Get the path to the default pipeline.star file."""
    return _get_star(path, "default_pipeline.star")


def _get_star(path: Path, name: str) -> Path | None:
    """Get the path to a .star file with the given name."""
    if path.is_dir() and (star := path.joinpath(name)).exists():
        return star
    if path.is_file() and path.name == name:
        return path
