from himena.plugins import register_widget_class
from himena_relion._widgets._main import register_job, JobWidgetBase, QRelionJobWidget
from himena_relion._widgets._view_nd import Q2DViewer, Q3DViewer
from himena_relion._widgets._spinbox import QIntWidget
from himena_relion.consts import Type

__all__ = [
    "register_job",
    "JobWidgetBase",
    "Q2DViewer",
    "Q3DViewer",
    "QIntWidget",
    "QRelionJobWidget",
]

register_widget_class(Type.RELION_JOB, QRelionJobWidget)
