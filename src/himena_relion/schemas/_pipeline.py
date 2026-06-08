import starfile_rs.schema.polars as schema


def _prepend_version_info(s: str) -> str:
    """Prepend the comment that tells RELION pipeliner to use the new version.

    There's a compatibility layer in relion_pipeliner.cpp:
    https://github.com/3dem/relion/blob/master/src/pipeliner.cpp#L1990
    We need to add the version string inside the STAR file.
    """
    return "# version 50001\n\n" + s


class RelionPipelineGeneral(schema.SingleDataModel):
    count: int = schema.Field("rlnPipeLineJobCounter")

    def to_string(self):
        return _prepend_version_info(super().to_string())


class RelionPipelineProcesses(schema.LoopDataModel):
    """Pipeline processes such as
    Import/job001/       None relion.importtomo  Failed"""

    process_name: schema.Series[str] = schema.Field("rlnPipeLineProcessName")
    alias: schema.Series[str] = schema.Field("rlnPipeLineProcessAlias")
    type_label: schema.Series[str] = schema.Field("rlnPipeLineProcessTypeLabel")
    status_label: schema.Series[str] = schema.Field("rlnPipeLineProcessStatusLabel")

    def to_string(self):
        return _prepend_version_info(super().to_string())


class RelionPipelineNodes(schema.LoopDataModel):
    name: schema.Series[str] = schema.Field("rlnPipeLineNodeName")
    type_label: schema.Series[str] = schema.Field("rlnPipeLineNodeTypeLabel")
    type_label_depth: schema.Series[int] = schema.Field(
        "rlnPipeLineNodeTypeLabelDepth", default=None
    )

    def make_type_map(self, depth: int | None = None) -> dict[str, str]:
        if depth is None:
            type_label = self.type_label
        else:
            type_label = [".".join(t.split(".")[:depth]) for t in self.type_label]
        return dict(zip(self.name, type_label))

    def to_string(self):
        return _prepend_version_info(super().to_string())


class RelionPipelineInputEdges(schema.LoopDataModel):
    """Pipeline input edges such as
    Import/job001/tilt_series.star     MotionCorr/job002/
    """

    from_node: schema.Series[str] = schema.Field("rlnPipeLineEdgeFromNode")
    process: schema.Series[str] = schema.Field("rlnPipeLineEdgeProcess")

    def to_string(self):
        return _prepend_version_info(super().to_string())


class RelionPipelineOutputEdges(schema.LoopDataModel):
    """Pipeline output edges such as
    Import/job001/ Import/job001/tilt_series.star
    """

    process: schema.Series[str] = schema.Field("rlnPipeLineEdgeProcess")
    to_node: schema.Series[str] = schema.Field("rlnPipeLineEdgeToNode")

    def to_string(self):
        return _prepend_version_info(super().to_string())


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

    def to_string(self):
        return (
            f"{self.general.to_string()}\n\n{self.processes.to_string()}\n\n"
            f"{self.nodes.to_string()}\n\n{self.input_edges.to_string()}\n\n"
            f"{self.output_edges.to_string()}"
        )
