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
    if model.type.startswith("relion_job.relion.refine3d"):
        include_classes = False
        model_suffix = "_half1_model"
    elif model.type.startswith("relion_job.relion.class3d"):
        include_classes = True
        model_suffix = "_model"
    elif model.type.startswith("relion_job.relion.initialmodel"):
        include_classes = True
        model_suffix = "_model"
    else:
        raise ValueError(f"Unsupported job type: {model.type}")
    widget = RefineJobPopup(
        ui, job_dir, include_classes=include_classes, model_suffix=model_suffix
    )
    ui.add_widget_as_popup(widget, title=f"Summary of {job_dir.job_normal_id()}")
