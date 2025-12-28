from himena_relion._job_class import connect_jobs
from himena_relion.relion5 import _builtins as _spa

connect_jobs(
    _spa.MotionCorr2Job,
    _spa.CtfEstimationJob,
    node_mapping={"corrected_micrographs.star": "input_star_mics"},
)
connect_jobs(
    _spa.MotionCorrOwnJob,
    _spa.CtfEstimationJob,
    node_mapping={"corrected_micrographs.star": "input_star_mics"},
)
connect_jobs(
    _spa.CtfEstimationJob,
    _spa.SelectMicrographsJob,
    node_mapping={"micrographs_ctf.star": "fn_mic"},
)
connect_jobs(
    _spa.CtfEstimationJob,
    _spa.ManualPickJob,
    node_mapping={"micrographs_ctf.star": "fn_in"},
)
for autopick_job in [
    _spa.AutoPickTemplateJob,
    _spa.AutoPickLogJob,
    _spa.AutoPickTopazTrain,
    _spa.AutoPickTopazPick,
]:
    connect_jobs(
        _spa.CtfEstimationJob,
        autopick_job,
        node_mapping={"micrographs_ctf.star": "fn_input_autopick"},
    )

connect_jobs(
    _spa.Class2DJob,
    _spa.SelectClassesInteractiveJob,
    node_mapping={"run_it001_classes.mrc": "fn_classes"},
)
# connect_jobs(
#     _spa.Class2DJob,
#     _spa.SelectClassesClassRanker,
#     node_mapping={"run_it001_classes.mrc": "fn_classes"},
# )
# connect_jobs(
#     _spa.SelectClassesInteractiveJob,
#     _spa.InitialModel,
# )
connect_jobs(
    _spa.Class3DJob,
    _spa.Refine3DJob,
    node_mapping={"run_class001.mrc": "fn_ref"},
)
connect_jobs(
    _spa.Refine3DJob,
    _spa.MaskCreationJob,
    node_mapping={"run_class001.mrc": "fn_in"},
)
connect_jobs(
    _spa.Refine3DJob,
    _spa.PostProcessJob,
    node_mapping={"run_half1_class001_unfil.mrc": "fn_in"},
)
