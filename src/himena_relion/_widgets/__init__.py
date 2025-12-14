from himena import StandardType
from himena.plugins import register_widget_class
from himena_relion._widgets._main import register_job, QRelionJobWidget
from himena_relion._widgets._job_widgets import (
    JobWidgetBase,
    QJobScrollArea,
    QRelionNodeItem,
)
from himena_relion._widgets._view_nd import Q2DViewer, Q3DViewer, Q2DFilterWidget
from himena_relion._widgets._spinbox import QIntWidget
from himena_relion._widgets._plot import QPlotCanvas
from himena_relion.consts import Type
from himena_relion._widgets._misc import spacer_widget

__all__ = [
    "register_job",
    "JobWidgetBase",
    "QJobScrollArea",
    "QPlotCanvas",
    "Q2DViewer",
    "Q3DViewer",
    "Q2DFilterWidget",
    "QIntWidget",
    "QRelionJobWidget",
    "QRelionNodeItem",
    "spacer_widget",
]

register_widget_class(Type.RELION_JOB, QRelionJobWidget)
register_widget_class(StandardType.IMAGE, Q3DViewer, priority=0)
