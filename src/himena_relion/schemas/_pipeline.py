import starfile_rs.schema.pandas as schema


class RelionPipelineGeneral(schema.SingleDataModel):
    count: int = schema.Field("rlnPipeLineJobCounter")


class RelionPipelineProcesses(schema.LoopDataModel):
    process_name: schema.Series[str] = schema.Field("rlnPipeLineProcessName")
    alias: schema.Series[str] = schema.Field("rlnPipeLineProcessAlias")
    type_label: schema.Series[str] = schema.Field("rlnPipeLineProcessTypeLabel")
    status_label: schema.Series[str] = schema.Field("rlnPipeLineProcessStatusLabel")


class RelionPipelineNodes(schema.LoopDataModel):
    name: schema.Series[str] = schema.Field("rlnPipeLineNodeName")
    type_label: schema.Series[str] = schema.Field("rlnPipeLineNodeTypeLabel")
    type_label_depth: schema.Series[int] = schema.Field("rlnPipeLineNodeTypeLabelDepth")


class RelionPipelineInputEdges(schema.LoopDataModel):
    from_node: schema.Series[str] = schema.Field("rlnPipeLineEdgeFromNode")
    process: schema.Series[str] = schema.Field("rlnPipeLineEdgeProcess")


class RelionPipelineOutputEdges(schema.LoopDataModel):
    process: schema.Series[str] = schema.Field("rlnPipeLineEdgeProcess")
    to_node: schema.Series[str] = schema.Field("rlnPipeLineEdgeToNode")


class RelionPipelineModel(schema.StarModel):
    """Complete RELION pipeline STAR file schema."""

    general: RelionPipelineGeneral = schema.Field("pipeline_general")
    processes: RelionPipelineProcesses = schema.Field("pipeline_processes")
    nodes: RelionPipelineNodes = schema.Field("pipeline_nodes")
    input_edges: RelionPipelineInputEdges = schema.Field(
        "pipeline_input_edges", default=None
    )
    output_edges: RelionPipelineOutputEdges = schema.Field(
        "pipeline_output_edges", default=None
    )

    General = RelionPipelineGeneral
    Processes = RelionPipelineProcesses
    Nodes = RelionPipelineNodes
    InputEdges = RelionPipelineInputEdges
    OutputEdges = RelionPipelineOutputEdges
