# version 50001

data_pipeline_general

_rlnPipeLineJobCounter                       2


# version 50001

data_pipeline_processes

loop_
_rlnPipeLineProcessName #1
_rlnPipeLineProcessAlias #2
_rlnPipeLineProcessTypeLabel #3
_rlnPipeLineProcessStatusLabel #4
Refine3D/job012/       None relion.refine3d.tomo    Running


# version 50001

data_pipeline_nodes

loop_
_rlnPipeLineNodeName #1
_rlnPipeLineNodeTypeLabel #2
_rlnPipeLineNodeTypeLabelDepth #3
Extract/job010/optimisation_set.star TomoOptimisationSet.star.relion            1
Reconstruct/job011/merged.mrc DensityMap.mrc            1
Refine3D/job012/run_data.star ParticleGroupMetadata.star.relion.refine3d            1
Refine3D/job012/run_optimiser.star OptimiserData.star.relion.refine3d            1
Refine3D/job012/run_half1_class001_unfil.mrc DensityMap.mrc.relion.halfmap.refine3d            1
Refine3D/job012/run_class001.mrc DensityMap.mrc.relion.refine3d            1
Refine3D/job012/run_optimisation_set.star TomoOptimisationSet.star.relion.refine3d            1


# version 50001

data_pipeline_input_edges

loop_
_rlnPipeLineEdgeFromNode #1
_rlnPipeLineEdgeProcess #2
Extract/job010/optimisation_set.star Refine3D/job012/
Reconstruct/job011/merged.mrc Refine3D/job012/


# version 50001

data_pipeline_output_edges

loop_
_rlnPipeLineEdgeProcess #1
_rlnPipeLineEdgeToNode #2
Refine3D/job012/ Refine3D/job012/run_data.star
Refine3D/job012/ Refine3D/job012/run_optimiser.star
Refine3D/job012/ Refine3D/job012/run_half1_class001_unfil.mrc
Refine3D/job012/ Refine3D/job012/run_class001.mrc
Refine3D/job012/ Refine3D/job012/run_optimisation_set.star
