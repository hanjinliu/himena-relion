from himena import MainWindow, WidgetDataModel
from himena.plugins import register_function
from himena_relion.io.job_utils import assert_job


@register_function(
    menus=[],
    types=[
        "relion_job.relion.refine3d",
        "relion_job.relion.refine3d_tomo",
        "relion_job.relion.class3d",
        "relion_job.relion.class3d_tomo",
        "relion_job.relion.initialmodel",
        "relion_job.relion.initialmodel_tomo",
    ],
    title="Show Summary",
    command_id="himena-relion:show-summary-panel",
)
def show_summary_panel(ui: MainWindow, model: WidgetDataModel):
    """Show the summary of the metrics over iterations."""
    from .popups._relion_refine import RefineJobPopup

    job_dir = assert_job(model)
    widget = RefineJobPopup(ui, job_dir)
    ui.add_widget_as_popup(widget, title=f"Summary of {job_dir.job_normal_id()}")
