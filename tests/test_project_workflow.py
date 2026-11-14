"""Tests of the workflow from a new RELION project.

`relion_pipeliner` is emulated by `FakeRelionPipeliner` (see `_fake_relion.py`).
"""

from pathlib import Path

from himena import MainWindow
from himena.testing import choose_one_dialog_response

from himena_relion._job_dir import JobDirectory
from himena_relion._pipeline import NodeStatus, RelionDefaultPipeline
from himena_relion.consts import DEFAULT_PIPELINE_STAR, NODES_DIR, FileNames
from himena_relion.hijack import _base
from himena_relion.io import _impl
from himena_relion.relion5._builtins import ImportMoviesJob, MotionCorrOwnJob
from himena_relion.schemas import RelionPipelineModel

from ._fake_relion import (
    FakeRelionPipeliner,
    check_scheduled_jobs as _check_scheduled_jobs,
    default_kwargs as _default_kwargs,
    input_edges as _input_edges,
    output_edges as _output_edges,
    read_blocks as _read_blocks,
    read_pipeline as _read_pipeline,
    start_new_project as _start_new_project,
    statuses as _statuses,
    write_blocks as _write_blocks,
)

IMPORT_JOB = "Import/job001/"
MOTIONCORR_JOB = "MotionCorr/job002/"
MOVIES_STAR = "Import/job001/movies.star"
MICROGRAPHS_STAR = "MotionCorr/job002/corrected_micrographs.star"
LOGFILE_PDF = "MotionCorr/job002/logfile.pdf"

def _create_import_job(rln_dir: Path) -> Path | None:
    return ImportMoviesJob.create_job(
        _cwd=rln_dir, **_default_kwargs(ImportMoviesJob, fn_in_raw="Movies/*.tif")
    )


def _create_motioncorr_job(rln_dir: Path) -> Path | None:
    return MotionCorrOwnJob.create_job(
        _cwd=rln_dir, **_default_kwargs(MotionCorrOwnJob, input_star_mics=MOVIES_STAR)
    )


def _flowchart_edges(rln_dir: Path) -> dict[str, list[str]]:
    """Map from each job to its parent files, as shown in the flow chart."""
    pipeline = RelionDefaultPipeline.from_pipeline_star(rln_dir / DEFAULT_PIPELINE_STAR)
    return {
        job.path.as_posix(): [
            f"{parent.node.path.as_posix()}/{parent.filename}" for parent in job.parents
        ]
        for job in pipeline.iter_nodes()
    }


def test_import_then_motioncorr(
    himena_ui: MainWindow, in_project: Path, relion: FakeRelionPipeliner
):
    path = in_project / DEFAULT_PIPELINE_STAR

    # Start a new project. There are no jobs yet.
    _start_new_project(himena_ui, in_project)
    pipeline = RelionDefaultPipeline.from_pipeline_star(path)
    assert list(pipeline.iter_nodes()) == []

    # Import: the job has no inputs, so that it can be run immediately.
    assert _create_import_job(in_project) == in_project / IMPORT_JOB
    assert "data_pipeline_input_edges" not in path.read_text()
    pipeline = _read_pipeline(in_project)
    assert pipeline.general.count == 2
    assert _statuses(pipeline) == {IMPORT_JOB: "Scheduled"}
    assert list(pipeline.nodes.name) == [MOVIES_STAR]
    assert _input_edges(pipeline) == []
    assert _output_edges(pipeline) == [(IMPORT_JOB, MOVIES_STAR)]
    assert _flowchart_edges(in_project) == {"Import/job001": []}
    assert JobDirectory(in_project / IMPORT_JOB).is_scheduled()

    _check_scheduled_jobs(in_project)
    assert relion.run_calls == [IMPORT_JOB]
    assert _statuses(_read_pipeline(in_project)) == {IMPORT_JOB: "Running"}
    # the running job is not executed again
    _check_scheduled_jobs(in_project)
    assert relion.run_calls == [IMPORT_JOB]

    relion.finish(IMPORT_JOB)
    _check_scheduled_jobs(in_project)
    assert relion.run_calls == [IMPORT_JOB]
    assert _statuses(_read_pipeline(in_project)) == {IMPORT_JOB: "Succeeded"}

    # MotionCorr: the input is ready.
    assert _create_motioncorr_job(in_project) == in_project / MOTIONCORR_JOB
    pipeline = _read_pipeline(in_project)
    assert pipeline.general.count == 3
    assert _statuses(pipeline) == {IMPORT_JOB: "Succeeded", MOTIONCORR_JOB: "Scheduled"}
    assert _input_edges(pipeline) == [(MOVIES_STAR, MOTIONCORR_JOB)]

    _check_scheduled_jobs(in_project)
    assert relion.run_calls == [IMPORT_JOB, MOTIONCORR_JOB]
    assert _statuses(_read_pipeline(in_project))[MOTIONCORR_JOB] == "Running"
    relion.finish(MOTIONCORR_JOB)
    _check_scheduled_jobs(in_project)
    assert relion.run_calls == [IMPORT_JOB, MOTIONCORR_JOB]

    pipeline = _read_pipeline(in_project)
    assert pipeline.general.count == 3
    assert _statuses(pipeline) == {IMPORT_JOB: "Succeeded", MOTIONCORR_JOB: "Succeeded"}
    assert list(pipeline.processes.type_label) == [
        "relion.import.movies",
        "relion.motioncorr.own",
    ]
    assert list(pipeline.nodes.name) == [MOVIES_STAR, MICROGRAPHS_STAR, LOGFILE_PDF]
    assert _input_edges(pipeline) == [(MOVIES_STAR, MOTIONCORR_JOB)]
    assert _output_edges(pipeline) == [
        (IMPORT_JOB, MOVIES_STAR),
        (MOTIONCORR_JOB, MICROGRAPHS_STAR),
        (MOTIONCORR_JOB, LOGFILE_PDF),
    ]
    assert _flowchart_edges(in_project) == {
        "Import/job001": [],
        "MotionCorr/job002": [MOVIES_STAR],
    }
    default = RelionDefaultPipeline.from_pipeline_star(path)
    assert [job.status for job in default.iter_nodes()] == [NodeStatus.SUCCEEDED] * 2


def test_motioncorr_waits_for_import(
    himena_ui: MainWindow, in_project: Path, relion: FakeRelionPipeliner
):
    _start_new_project(himena_ui, in_project)
    assert _create_import_job(in_project) == in_project / IMPORT_JOB
    # MotionCorr is scheduled before Import is run
    assert _create_motioncorr_job(in_project) is None
    pipeline = _read_pipeline(in_project)
    assert _statuses(pipeline) == {IMPORT_JOB: "Scheduled", MOTIONCORR_JOB: "Scheduled"}
    assert _input_edges(pipeline) == [(MOVIES_STAR, MOTIONCORR_JOB)]

    _check_scheduled_jobs(in_project)
    assert relion.run_calls == [IMPORT_JOB]
    pipeline = _read_pipeline(in_project)
    assert _statuses(pipeline) == {IMPORT_JOB: "Running", MOTIONCORR_JOB: "Scheduled"}

    relion.finish(IMPORT_JOB)
    _check_scheduled_jobs(in_project)
    assert relion.run_calls == [IMPORT_JOB, MOTIONCORR_JOB]
    pipeline = _read_pipeline(in_project)
    assert _statuses(pipeline) == {IMPORT_JOB: "Succeeded", MOTIONCORR_JOB: "Running"}
    assert _input_edges(pipeline) == [(MOVIES_STAR, MOTIONCORR_JOB)]


def test_overwrite_jobs(
    himena_ui: MainWindow, in_project: Path, relion: FakeRelionPipeliner
):
    path = in_project / DEFAULT_PIPELINE_STAR
    _start_new_project(himena_ui, in_project)
    _create_import_job(in_project)
    _check_scheduled_jobs(in_project)
    relion.finish(IMPORT_JOB)

    # overwrite the job in the project without any input edges
    import_dir = JobDirectory(in_project / IMPORT_JOB)
    ImportMoviesJob(import_dir).edit_and_run_job(
        **_default_kwargs(ImportMoviesJob, fn_in_raw="Movies/*.mrc")
    )
    assert import_dir.get_job_param("fn_in_raw") == "Movies/*.mrc"
    assert not import_dir.path.joinpath(FileNames.EXIT_SUCCESS).exists()
    assert "data_pipeline_input_edges" not in path.read_text()
    pipeline = _read_pipeline(in_project)
    assert pipeline.general.count == 2
    assert _statuses(pipeline) == {IMPORT_JOB: "Scheduled"}
    assert list(pipeline.nodes.name) == [MOVIES_STAR]
    assert _input_edges(pipeline) == []
    assert _output_edges(pipeline) == [(IMPORT_JOB, MOVIES_STAR)]
    job_pipeline = RelionPipelineModel.validate_file(import_dir.job_pipeline())
    assert _input_edges(job_pipeline) == []
    assert _output_edges(job_pipeline) == [(IMPORT_JOB, MOVIES_STAR)]

    _check_scheduled_jobs(in_project)
    assert relion.run_calls == [IMPORT_JOB, IMPORT_JOB]
    relion.finish(IMPORT_JOB)

    # overwrite the job with an input
    _create_motioncorr_job(in_project)
    _check_scheduled_jobs(in_project)
    relion.finish(MOTIONCORR_JOB)
    mcor_dir = JobDirectory(in_project / MOTIONCORR_JOB)
    MotionCorrOwnJob(mcor_dir).edit_and_run_job(
        **_default_kwargs(MotionCorrOwnJob, input_star_mics=MOVIES_STAR, bfactor=200)
    )
    pipeline = _read_pipeline(in_project)
    assert _statuses(pipeline) == {IMPORT_JOB: "Succeeded", MOTIONCORR_JOB: "Scheduled"}
    assert list(pipeline.nodes.name) == [MOVIES_STAR, MICROGRAPHS_STAR, LOGFILE_PDF]
    assert _input_edges(pipeline) == [(MOVIES_STAR, MOTIONCORR_JOB)]
    assert len(_output_edges(pipeline)) == 3
    job_pipeline = RelionPipelineModel.validate_file(mcor_dir.job_pipeline())
    assert list(job_pipeline.nodes.name) == [MOVIES_STAR, MICROGRAPHS_STAR, LOGFILE_PDF]
    assert _input_edges(job_pipeline) == [(MOVIES_STAR, MOTIONCORR_JOB)]


def test_trash_and_restore_jobs(
    himena_ui: MainWindow, in_project: Path, relion: FakeRelionPipeliner
):
    _start_new_project(himena_ui, in_project)
    _create_import_job(in_project)
    _check_scheduled_jobs(in_project)
    relion.finish(IMPORT_JOB)
    _create_motioncorr_job(in_project)
    _check_scheduled_jobs(in_project)
    relion.finish(MOTIONCORR_JOB)

    # trash MotionCorr: no input edges are left
    with choose_one_dialog_response(himena_ui, True):
        _impl.trash_job(himena_ui, JobDirectory(in_project / MOTIONCORR_JOB))
    assert not in_project.joinpath(MOTIONCORR_JOB).exists()
    pipeline = _read_pipeline(in_project)
    assert _statuses(pipeline) == {IMPORT_JOB: "Succeeded"}
    assert list(pipeline.nodes.name) == [MOVIES_STAR]
    assert _input_edges(pipeline) == []
    assert _output_edges(pipeline) == [(IMPORT_JOB, MOVIES_STAR)]

    # trash Import in the project without any input edges
    with choose_one_dialog_response(himena_ui, True):
        _impl.trash_job(himena_ui, JobDirectory(in_project / IMPORT_JOB))
    assert not in_project.joinpath(IMPORT_JOB).exists()
    default = RelionDefaultPipeline.from_pipeline_star(
        in_project / DEFAULT_PIPELINE_STAR
    )
    assert list(default.iter_nodes()) == []

    # restore both
    _impl.restore_trashed_jobs(in_project, ["Import/job001", "MotionCorr/job002"])
    assert in_project.joinpath(MOVIES_STAR).exists()
    assert in_project.joinpath(MICROGRAPHS_STAR).exists()
    pipeline = _read_pipeline(in_project)
    assert _statuses(pipeline) == {IMPORT_JOB: "Succeeded", MOTIONCORR_JOB: "Succeeded"}
    assert list(pipeline.nodes.name) == [MOVIES_STAR, MICROGRAPHS_STAR, LOGFILE_PDF]
    assert _input_edges(pipeline) == [(MOVIES_STAR, MOTIONCORR_JOB)]
    assert _output_edges(pipeline) == [
        (IMPORT_JOB, MOVIES_STAR),
        (MOTIONCORR_JOB, MICROGRAPHS_STAR),
        (MOTIONCORR_JOB, LOGFILE_PDF),
    ]


def test_overwrite_from_scheduler(
    himena_ui: MainWindow, in_project: Path, relion: FakeRelionPipeliner
):
    _start_new_project(himena_ui, in_project)
    _create_import_job(in_project)
    _check_scheduled_jobs(in_project)
    relion.finish(IMPORT_JOB)
    import_dir = JobDirectory(in_project / IMPORT_JOB)

    # no input edges in the project: overwritten without asking
    scheduler = _impl.overwrite_relion_job(himena_ui, import_dir)
    scheduler._exec_btn.click()
    assert _statuses(_read_pipeline(in_project)) == {IMPORT_JOB: "Scheduled"}
    _check_scheduled_jobs(in_project)
    relion.finish(IMPORT_JOB)

    # the output is used by MotionCorr: the user is asked
    _create_motioncorr_job(in_project)
    scheduler = _impl.overwrite_relion_job(himena_ui, import_dir)
    with choose_one_dialog_response(himena_ui, True):  # cancel
        scheduler._exec_btn.click()
    assert _statuses(_read_pipeline(in_project))[IMPORT_JOB] == "Succeeded"
    assert in_project.joinpath(MOVIES_STAR).exists()
    with choose_one_dialog_response(himena_ui, False):  # overwrite
        scheduler._exec_btn.click()
    pipeline = _read_pipeline(in_project)
    assert _statuses(pipeline) == {IMPORT_JOB: "Scheduled", MOTIONCORR_JOB: "Scheduled"}
    assert _input_edges(pipeline) == [(MOVIES_STAR, MOTIONCORR_JOB)]


def test_touch_output_node_files(
    himena_ui: MainWindow, in_project: Path, relion: FakeRelionPipeliner
):
    _start_new_project(himena_ui, in_project)
    _create_import_job(in_project)
    _check_scheduled_jobs(in_project)
    relion.finish(IMPORT_JOB)
    import_dir = JobDirectory(in_project / IMPORT_JOB)
    touched = _base.touch_output_node_files(import_dir)
    assert touched == [in_project / NODES_DIR / "MicrographMoviesData" / MOVIES_STAR]
    assert touched[0].exists()

    # nothing to touch if the project does not have any output edges
    counter, blocks = _read_blocks(relion.path)
    blocks["pipeline_output_edges"] = []
    _write_blocks(relion.path, counter, blocks)
    assert "data_pipeline_output_edges" not in relion.path.read_text()
    assert _base.touch_output_node_files(import_dir) == []
