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
    node_mapping={"tilt_series_ctf.star": "fn_mic"},
)
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
