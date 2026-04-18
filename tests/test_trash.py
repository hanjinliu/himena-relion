from pathlib import Path
from himena import MainWindow
from himena.testing import choose_one_dialog_response
from himena_relion._job_dir import JobDirectory
from himena_relion._widgets._trash_widget import QTrashWidget, _copy_job_paths, _delete_permanently
from himena_relion.io._impl import trash_job, restore_trashed_jobs, normalize_job_id
from himena_relion.schemas import RelionPipelineModel
from ._utils import DEFAULT_PIPELINES_DIR

def _extract_job_pipeline(pipeline: RelionPipelineModel, job_name: str) -> RelionPipelineModel:
    job_name = normalize_job_id(job_name)

    return RelionPipelineModel.validate_dict(
        {
            "pipeline_general": RelionPipelineModel.General(count= 3),
            "pipeline_processes": pipeline.processes.dataframe[pipeline.processes.process_name == job_name],
            "pipeline_nodes": pipeline.nodes.dataframe[pipeline.nodes.name.str.startswith(job_name)],
            "pipeline_input_edges": pipeline.input_edges.dataframe[pipeline.input_edges.process == job_name],
            "pipeline_output_edges": pipeline.output_edges.dataframe[pipeline.output_edges.process == job_name],
        }
    )

_JOB_STAR_TEXT = """data_job

_rlnJobTypeLabel             relion.XXX
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
        ParameterA    1
"""

def _prep_project(tmpdir):
    rln_dir = Path(tmpdir)

    # prepare default_pipeline.star
    path = Path(tmpdir) / "default_pipeline.star"
    txt = (DEFAULT_PIPELINES_DIR / "full.star").read_text()
    path.write_text(txt)

    # prepare job directories
    pipeline = RelionPipelineModel.validate_file(path)
    for pname in pipeline.processes.process_name:
        job_dir = rln_dir / pname
        job_dir.mkdir(parents=True)
        job_dir.joinpath("job.star").write_text(_JOB_STAR_TEXT)
        _extract_job_pipeline(pipeline, pname).write(job_dir / "job_pipeline.star")

    # prepare .Nodes directory
    (rln_dir / ".Nodes").mkdir()
    typemap = pipeline.nodes.make_type_map(depth=1)

    for to_node in pipeline.output_edges.to_node:
        type_label = typemap[to_node]
        filepath = rln_dir / ".Nodes" / type_label / to_node
        filepath.parent.mkdir(parents=True)
        filepath.touch()
    return rln_dir

def test_trash_untrash(himena_ui: MainWindow, tmpdir):
    rln_dir = _prep_project(tmpdir)

    assert (rln_dir / "Import/job001").exists()
    assert (rln_dir / "MotionCorr/job002").exists()
    assert (rln_dir / "CtfFind/job003").exists()
    himena_ui.read_file(rln_dir / "default_pipeline.star")
    himena_ui.read_file(rln_dir / "MotionCorr/job002")
    himena_ui.read_file(rln_dir / "Import/job001")
    assert "job002" in himena_ui.tabs.names
    with choose_one_dialog_response(himena_ui, True):
        trash_job(himena_ui, JobDirectory(rln_dir / "MotionCorr/job002"))
    assert "job002" not in himena_ui.tabs.names
    assert (rln_dir / "Import/job001").exists()
    assert not (rln_dir / "MotionCorr/job002").exists()
    assert not (rln_dir / "CtfFind/job003").exists()
    restore_trashed_jobs(rln_dir, ["MotionCorr/job002/"])
    assert (rln_dir / "Import/job001").exists()
    assert (rln_dir / "MotionCorr/job002").exists()
    assert not (rln_dir / "CtfFind/job003").exists()
    restore_trashed_jobs(rln_dir, ["CtfFind/job003/"])
    assert (rln_dir / "Import/job001").exists()
    assert (rln_dir / "MotionCorr/job002").exists()
    assert (rln_dir / "CtfFind/job003").exists()

def test_trash_widget(himena_ui: MainWindow, tmpdir):
    rln_dir = _prep_project(tmpdir)
    himena_ui.read_file(rln_dir / "default_pipeline.star")
    with choose_one_dialog_response(himena_ui, True):
        trash_job(himena_ui, JobDirectory(rln_dir / "MotionCorr/job002"))
    win = himena_ui.read_file(rln_dir / "Trash")
    assert isinstance(win.widget, QTrashWidget)
    assert win.widget.trash_dir() == rln_dir / "Trash"

    win.widget._make_context_menu()
    win.widget._job_list_widget.setCurrentRow(0)
    win.widget._make_context_menu()

    _copy_job_paths(["MotionCorr/job002/"], rln_dir / "Trash")
    assert (rln_dir / "Trash" / "MotionCorr/job002").exists()
    with choose_one_dialog_response(himena_ui, True):
        _delete_permanently(["MotionCorr/job002/"], rln_dir / "Trash")
    assert not (rln_dir / "Trash" / "MotionCorr/job002").exists()
