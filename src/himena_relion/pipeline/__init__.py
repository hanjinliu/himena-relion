from himena.plugins import register_widget_class
from himena_relion._pipeline import RelionDefaultPipeline
from himena_relion.pipeline.widgets import QRelionPipelineFlowChart
from himena_relion.consts import Type

__all__ = ["QRelionPipelineFlowChart", "RelionDefaultPipeline"]

register_widget_class(Type.RELION_PIPELINE, QRelionPipelineFlowChart)
