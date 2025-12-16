from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from himena import WidgetDataModel, create_text_model
from himena.plugins import register_function
from himena_relion.consts import Type, MenuId

if TYPE_CHECKING:
    from himena_relion._job import JobDirectory


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Open job.star as text",
    command_id="himena-relion:open-job-star",
)
def open_relion_job_star(model: WidgetDataModel) -> WidgetDataModel:
    job_dir = assert_job(model)
    job_star_path = job_dir.job_star()
    return create_text_model(
        job_star_path.read_text(),
        title=f"{job_dir.path.stem}/{job_star_path.name}",
        extension_default=".star",
    )


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Open job_pipeline.star as text",
    command_id="himena-relion:open-job-pipeline-star",
)
def open_relion_job_pipeline_star(model: WidgetDataModel) -> WidgetDataModel:
    job_dir = assert_job(model)
    job_star_path = job_dir.job_pipeline()
    return create_text_model(
        job_star_path.read_text(),
        title=f"{job_dir.path.stem}/{job_star_path.name}",
        extension_default=".star",
    )


@register_function(
    menus=[MenuId.RELION_UTILS],
    types=[Type.RELION_JOB],
    title="Clone this job",
    command_id="himena-relion:clone-job",
)
def clone_relion_job(model: WidgetDataModel) -> WidgetDataModel:
    """Clone this RELION job."""
    job_dir = assert_job(model)
    subprocess.run(
        ["relion_pipeliner", "--addJobFromStar", job_dir.job_star().as_posix()],
        check=True,
    )


def assert_job(model: WidgetDataModel) -> JobDirectory:
    from himena_relion._job import JobDirectory

    value = model.value
    if not isinstance(value, JobDirectory):
        raise TypeError(f"Expected JobDirectory object, got {type(value)}")
    return value
