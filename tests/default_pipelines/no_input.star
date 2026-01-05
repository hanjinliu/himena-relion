# version 50001

data_pipeline_general

_rlnPipeLineJobCounter                      2


# version 50001

data_pipeline_processes

loop_
_rlnPipeLineProcessName #1
_rlnPipeLineProcessAlias #2
_rlnPipeLineProcessTypeLabel #3
_rlnPipeLineProcessStatusLabel #4
Import/job001/       None relion.importtomo  Succeeded


# version 50001

data_pipeline_nodes

loop_
_rlnPipeLineNodeName #1
_rlnPipeLineNodeTypeLabel #2
_rlnPipeLineNodeTypeLabelDepth #3
Import/job001/tilt_series.star TomogramGroupMetadata.star.relion.tomo.import


# version 50001

data_pipeline_output_edges

loop_
_rlnPipeLineEdgeProcess #1
_rlnPipeLineEdgeToNode #2
Import/job001/ Import/job001/tilt_series.star
