from __future__ import annotations

import os
from pathlib import Path
import mrcfile
import numpy as np
from himena import StandardType, WidgetDataModel, create_image_model
from himena.standards.model_meta import DimAxis
from himena.plugins import register_reader_plugin
from himena_relion.consts import Type


@register_reader_plugin(priority=0, module="himena_relion.io")
def read_density_map(path: Path) -> WidgetDataModel:
    with mrcfile.open(path) as mrc:
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
    if path.suffix.rstrip("~") in (".mrc", ".map") or path.suffixes == [".map", ".gz"]:
        return StandardType.IMAGE


@register_reader_plugin(priority=10, module="himena_relion.io")
def read_mrcs(path: Path) -> WidgetDataModel:
    with mrcfile.open(path) as mrc:
        arr = np.asarray(mrc.data)
        voxel_size = mrc.voxel_size
    return create_image_model(
        arr,
        axes=_prep_3d_axes(voxel_size),
        extension_default=".mrcs",
    )


@read_mrcs.define_matcher
def _(path: Path):
    if path.suffix.rstrip("~") == ".mrcs":
        return StandardType.IMAGE


@register_reader_plugin(priority=20, module="himena_relion.io")
def read_mrc(path: Path) -> WidgetDataModel:
    """A convenient reader for MRC files."""
    with mrcfile.open(path, header_only=True) as mrc:
        nz, ny, nx = mrc.header.nx, mrc.header.ny, mrc.header.nz
    if (1 < nz <= 512) and (1 < ny <= 512) and (1 < nx <= 512):
        # Likely a 3D map
        return read_density_map(path)

    with mrcfile.open(path) as mrc:
        arr = np.asarray(mrc.data)
        voxel_size = mrc.voxel_size
    if arr.ndim == 4:
        axes = [DimAxis(name="t")] + _prep_3d_axes(voxel_size)
    elif arr.ndim == 3:
        axes = _prep_3d_axes(voxel_size)
    else:
        axes = None
    return create_image_model(
        arr,
        axes=axes,
        extension_default=".mrc",
    )


@read_mrc.define_matcher
def _(path: Path):
    if path.suffix.rstrip("~") in (".mrc", ".map") or path.suffixes == [".map", ".gz"]:
        return StandardType.IMAGE


@register_reader_plugin(priority=500, module="himena_relion.io")
def read_relion_job(path: Path) -> WidgetDataModel:
    if job_star := _get_job_star(path):
        from himena_relion._job_dir import JobDirectory

        job_dir = JobDirectory.from_job_star(job_star)
        return WidgetDataModel(
            value=job_dir,
            type=job_dir.himena_model_type(),
            title=job_star.parent.name,
        ).use_tab()
    raise ValueError(f"Expected an existing job.star file, got {path}")


@read_relion_job.define_matcher
def _(path: Path):
    if _get_job_star(path) is not None:
        return Type.RELION_JOB
    return None


@register_reader_plugin(priority=500, module="himena_relion.io")
def read_relion_pipeline(path: Path) -> WidgetDataModel:
    """Read a RELION default_pipeline.star file."""
    if pipeline_star := _get_default_pipeline_star(path):
        from himena_relion.pipeline import RelionDefaultPipeline

        os.chdir(pipeline_star.parent)
        return WidgetDataModel(
            value=RelionDefaultPipeline.from_pipeline_star(pipeline_star),
            type=Type.RELION_PIPELINE,
            title="RELION Pipeline",
        ).use_dock_widget(area="left")
    raise ValueError(f"Expected an existing default_pipeline.star file, got {path}")


@read_relion_pipeline.define_matcher
def _(path: Path):
    if _get_default_pipeline_star(path) is not None:
        return Type.RELION_PIPELINE


@register_reader_plugin(priority=500, module="himena_relion.io")
def read_relion_trash_directory(path: Path) -> WidgetDataModel:
    """Read the trash directory of a RELION project."""
    if path.is_dir():
        return WidgetDataModel(
            value=path,
            type=Type.RELION_TRASH,
            title=path.name,
        ).use_tab()
    raise ValueError(f"Expected a Trash directory, got {path}")


@read_relion_trash_directory.define_matcher
def _(path: Path):
    if (
        path.is_dir()
        and path.name == "Trash"
        and path.parent.joinpath("default_pipeline.star").exists()
    ):
        return Type.RELION_TRASH


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


def _prep_3d_axes(voxel_size: np.recarray) -> list[DimAxis]:
    return [
        DimAxis(name="z", scale=voxel_size.z, unit="Å"),
        DimAxis(name="y", scale=voxel_size.y, unit="Å"),
        DimAxis(name="x", scale=voxel_size.x, unit="Å"),
    ]
