from __future__ import annotations

from typing import TYPE_CHECKING
from himena import MainWindow, WidgetDataModel, create_text_model
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
def clone_relion_job(ui: MainWindow, model: WidgetDataModel):
    """Clone this RELION job."""
    job_dir = assert_job(model)
    job_cls = job_dir._to_job_class()
    if job_cls is None:
        raise RuntimeError("Cannot determine job class.")
    scheduler = job_cls._show_scheduler_widget(ui, {})
    scheduler.update_by_job(job_cls)
    scheduler.set_parameters(job_dir.get_job_params_as_dict())
    scheduler.set_edit_mode(job_dir)


def assert_job(model: WidgetDataModel) -> JobDirectory:
    from himena_relion._job import JobDirectory

    value = model.value
    if not isinstance(value, JobDirectory):
        raise TypeError(f"Expected JobDirectory object, got {type(value)}")
    return value
