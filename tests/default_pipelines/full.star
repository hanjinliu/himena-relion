# version 50001

data_pipeline_general

_rlnPipeLineJobCounter                      4


# version 50001

data_pipeline_processes

loop_
_rlnPipeLineProcessName #1
_rlnPipeLineProcessAlias #2
_rlnPipeLineProcessTypeLabel #3
_rlnPipeLineProcessStatusLabel #4
Import/job001/       None relion.importtomo  Failed
MotionCorr/job002/       None relion.motioncorr.own  Succeeded
CtfFind/job003/       None relion.ctffind.ctffind4  Scheduled


# version 50001

data_pipeline_nodes

loop_
_rlnPipeLineNodeName #1
_rlnPipeLineNodeTypeLabel #2
_rlnPipeLineNodeTypeLabelDepth #3
Import/job001/tilt_series.star TomogramGroupMetadata.star.relion.tomo.import            1
MotionCorr/job002/corrected_tilt_series.star TomogramGroupMetadata.star.relion.tomo.motioncorr            1
MotionCorr/job002/logfile.pdf LogFile.pdf.relion.motioncorr            1


# version 50001

data_pipeline_input_edges

loop_
_rlnPipeLineEdgeFromNode #1
_rlnPipeLineEdgeProcess #2
Import/job001/tilt_series.star MotionCorr/job002/
MotionCorr/job002/corrected_tilt_series.star CtfFind/job003/
CtfFind/job003/tilt_series_ctf.star ExcludeTiltImages/job004/


# version 50001

data_pipeline_output_edges

loop_
_rlnPipeLineEdgeProcess #1
_rlnPipeLineEdgeToNode #2
Import/job001/ Import/job001/tilt_series.star
MotionCorr/job002/ MotionCorr/job002/corrected_tilt_series.star
MotionCorr/job002/ MotionCorr/job002/logfile.pdf
