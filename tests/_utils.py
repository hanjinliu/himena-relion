from pathlib import Path
from typing import Iterable
from himena_relion.schemas import RelionPipelineModel
from himena_relion.io._impl import normalize_job_id

def assert_param_name_match(a, b, allowed_diffs: Iterable[str] = ("other_args",)):
    a_set = set(a)
    b_set = set(b)
    allowed_diffs_set = set(allowed_diffs)
    only_in_a = a_set - b_set - allowed_diffs_set
    only_in_b = b_set - a_set - allowed_diffs_set
    assert len(only_in_a | only_in_b) == 0, (
        f"Parameter names do not match.\n"
        f"Only in first: {only_in_a}\n"
        f"Only in second: {only_in_b}"
    )

JOBS_DIR_SPA = Path(__file__).parent / "jobs_spa"
JOBS_DIR_TOMO = Path(__file__).parent / "jobs_tomo"
DEFAULT_PIPELINES_DIR = Path(__file__).parent / "default_pipelines"
JOB_PIPELINES_DIR = Path(__file__).parent / "job_pipelines"

def iter_spa_job_dirs():
    yield from _iter_job_dirs(JOBS_DIR_SPA)

def iter_tomo_job_dirs():
    yield from _iter_job_dirs(JOBS_DIR_TOMO)

def _iter_job_dirs(jobs_dir: Path) -> Iterable[str]:
    for file in jobs_dir.iterdir():
        if file.is_file():
            continue
        for subdir in file.iterdir():
            if subdir.is_dir() and subdir.name.startswith("job"):
                if (subdir / "job.star").exists():
                    yield subdir.relative_to(jobs_dir).as_posix()

def read_sample_job_pipeline_star(name: str):
    pipeline_path = JOB_PIPELINES_DIR / name
    return pipeline_path.read_text()

def _extract_job_pipeline(pipeline: RelionPipelineModel, job_name: str) -> RelionPipelineModel:
    job_name = normalize_job_id(job_name)

    return RelionPipelineModel.validate_dict(
        {
            "pipeline_general": RelionPipelineModel.General(count=3),
            "pipeline_processes": pipeline.processes.dataframe.filter(pipeline.processes.process_name == job_name),
            "pipeline_nodes": pipeline.nodes.dataframe.filter(pipeline.nodes.name.str.starts_with(job_name)),
            "pipeline_input_edges": pipeline.input_edges.dataframe.filter(pipeline.input_edges.process == job_name),
            "pipeline_output_edges": pipeline.output_edges.dataframe.filter(pipeline.output_edges.process == job_name),
        }
    )

def prep_relion_project(tmpdir):
    rln_dir = Path(tmpdir)

    # prepare default_pipeline.star
    path = Path(tmpdir) / "default_pipeline.star"
    txt = (DEFAULT_PIPELINES_DIR / "full.star").read_text()
    path.write_text(txt)

    # prepare job directories
    pipeline = RelionPipelineModel.validate_file(path)
    for pname in pipeline.processes.process_name:
        job_star_template_path = JOBS_DIR_SPA / pname.split("/")[0] / "job001" / "job.star"
        job_dir = rln_dir / pname
        job_dir.mkdir(parents=True)
        job_dir.joinpath("job.star").write_text(job_star_template_path.read_text())
        _extract_job_pipeline(pipeline, pname).write(job_dir / "job_pipeline.star")

    # prepare .Nodes directory
    (rln_dir / ".Nodes").mkdir()
    typemap = pipeline.nodes.make_type_map(depth=1)

    for to_node in pipeline.output_edges.to_node:
        type_label = typemap[to_node]
        filepath = rln_dir / ".Nodes" / type_label / to_node
        filepath.parent.mkdir(parents=True)
        filepath.touch()
    assert (rln_dir / "Import/job001").exists()
    assert (rln_dir / "MotionCorr/job002").exists()
    assert (rln_dir / "CtfFind/job003").exists()
    return rln_dir
