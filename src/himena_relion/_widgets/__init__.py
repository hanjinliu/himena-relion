from himena import StandardType
from himena.plugins import register_widget_class
from himena_relion.consts import Type
from himena_relion._job_dir import ExternalJobDirectory
from himena_relion._widgets._main import register_job, QRelionJobWidget
from himena_relion._widgets._widgets_external import QExternalJobView
from himena_relion._widgets._job_widgets import (
    JobWidgetBase,
    QJobScrollArea,
    QRelionNodeItem,
)
from himena_relion._widgets._view_nd import Q2DViewer, Q3DViewer, Q2DFilterWidget
from himena_relion._widgets._spinbox import QIntWidget, QIntChoiceWidget
from himena_relion._widgets._plot import QPlotCanvas
from himena_relion._widgets._misc import (
    spacer_widget,
    QMicrographListWidget,
    QImageViewTextEdit,
    QNumParticlesLabel,
)
from himena_relion._widgets._job_edit import QJobScheduler

__all__ = [
    "register_job",
    "JobWidgetBase",
    "QJobScrollArea",
    "QPlotCanvas",
    "Q2DViewer",
    "Q3DViewer",
    "Q2DFilterWidget",
    "QIntWidget",
    "QIntChoiceWidget",
    "QRelionJobWidget",
    "QRelionNodeItem",
    "QJobScheduler",
    "QMicrographListWidget",
    "QImageViewTextEdit",
    "QNumParticlesLabel",
    "spacer_widget",
]

register_widget_class(Type.RELION_JOB, QRelionJobWidget)
register_widget_class(StandardType.IMAGE, Q3DViewer, priority=0)

register_job(ExternalJobDirectory)(QExternalJobView)
