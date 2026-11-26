from himena.plugins import register_widget_class, add_default_status_tip
from himena_relion._pipeline import RelionDefaultPipeline
from himena_relion.pipeline.widgets import QRelionPipelineFlowChart
from himena_relion.consts import Type

__all__ = ["QRelionPipelineFlowChart", "RelionDefaultPipeline"]

register_widget_class(Type.RELION_PIPELINE, QRelionPipelineFlowChart)

add_default_status_tip(short="RELION", long="Press `P` to peek the job.")
