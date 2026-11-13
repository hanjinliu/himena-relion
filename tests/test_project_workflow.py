"""Tests of the workflow from a new RELION project.

`relion_pipeliner` is emulated by `FakeRelionPipeliner`, which edits
default_pipeline.star as RELION does. Note that RELION does not write the blocks
without any rows, so that a new project does not have `pipeline_input_edges` until a
job with inputs is added.
"""

import re
import shutil
from pathlib import Path

import pytest
from himena import MainWindow
from himena.testing import choose_one_dialog_response, file_dialog_response
from starfile_rs import read_star

from himena_relion import _job_class, pipeline_watcher
from himena_relion._job_dir import JobDirectory
from himena_relion._pipeline import NodeStatus, RelionDefaultPipeline
from himena_relion.consts import DEFAULT_PIPELINE_STAR, FileNames
from himena_relion.io import _impl
from himena_relion.relion5._builtins import ImportMoviesJob, MotionCorrOwnJob
from himena_relion.schemas import JobStarModel, RelionPipelineModel

IMPORT_JOB = "Import/job001/"
MOTIONCORR_JOB = "MotionCorr/job002/"
MOVIES_STAR = "Import/job001/movies.star"
MICROGRAPHS_STAR = "MotionCorr/job002/corrected_micrographs.star"
LOGFILE_PDF = "MotionCorr/job002/logfile.pdf"

# type label -> (directory name, [(output file, node type label)], [input parameters])
_JOB_SPECS = {
    "relion.import.movies": (
        "Import",
        [("movies.star", "MicrographMoviesData.star.relion")],
        [],
    ),
    "relion.motioncorr.own": (
        "MotionCorr",
        [
            ("corrected_micrographs.star", "MicrographsData.star.relion.motioncorr"),
            ("logfile.pdf", "LogFile.pdf.relion.motioncorr"),
        ],
        ["input_star_mics"],
    ),
}
_BLOCKS = {
    "pipeline_processes": [
        "rlnPipeLineProcessName",
        "rlnPipeLineProcessAlias",
        "rlnPipeLineProcessTypeLabel",
        "rlnPipeLineProcessStatusLabel",
    ],
    "pipeline_nodes": [
        "rlnPipeLineNodeName",
        "rlnPipeLineNodeTypeLabel",
        "rlnPipeLineNodeTypeLabelDepth",
    ],
    "pipeline_input_edges": ["rlnPipeLineEdgeFromNode", "rlnPipeLineEdgeProcess"],
    "pipeline_output_edges": ["rlnPipeLineEdgeProcess", "rlnPipeLineEdgeToNode"],
}


def _read_blocks(path: Path) -> tuple[int, dict[str, list[tuple[str, ...]]]]:
    """Read the job counter and the rows of each block of a pipeline STAR file."""
    text = path.read_text()
    counter = int(re.search(r"_rlnPipeLineJobCounter\s+(\d+)", text).group(1))
    star = read_star(path)
    blocks: dict[str, list[tuple[str, ...]]] = {}
    for name, columns in _BLOCKS.items():
        if name in star.keys():
            df = star[name].trust_loop().to_polars().select(columns)
            blocks[name] = [tuple(str(v) for v in row) for row in df.rows()]
        else:
            blocks[name] = []
    return counter, blocks


def _write_blocks(path: Path, counter: int, blocks: dict[str, list[tuple[str, ...]]]):
    """Write a pipeline STAR file as RELION does (blocks without rows are skipped)."""
    lines = [
        "",
        "# version 50001",
        "",
        "data_pipeline_general",
        "",
        f"_rlnPipeLineJobCounter                       {counter}",
        " ",
    ]
    for name, columns in _BLOCKS.items():
        if len(rows := blocks[name]) == 0:
            continue
        lines += ["", "# version 50001", "", f"data_{name}", "", "loop_ "]
        lines += [f"_{column} #{i + 1} " for i, column in enumerate(columns)]
        lines += [" ".join(row) + " " for row in rows]
        lines.append(" ")
    path.write_text("\n".join(lines) + "\n", newline="\n")


class FakeRelionPipeliner:
    """Emulate `relion_pipeliner --addJobFromStar` and `relion_pipeliner --RunJobs`."""

    def __init__(self, rln_dir: Path):
        self.rln_dir = rln_dir
        self.run_calls: list[str] = []

    @property
    def path(self) -> Path:
        return self.rln_dir / DEFAULT_PIPELINE_STAR

    def add_job_from_star(self, job_star_path: Path, cwd: Path, *, alias=None):
        assert Path(cwd) == self.rln_dir
        job_star = JobStarModel.validate_file(job_star_path)
        params = job_star.joboptions_values.to_dict()
        dirname, outputs, input_keys = _JOB_SPECS[job_star.job.job_type_label]
        counter, blocks = _read_blocks(self.path)
        job_id = f"{dirname}/job{counter:03d}/"
        inputs = [params[key] for key in input_keys if params[key] != ""]
        types = {row[0]: row[1] for row in blocks["pipeline_nodes"]}

        process = (job_id, "None", job_star.job.job_type_label, "Scheduled")
        nodes = [(f"{job_id}{name}", label, "1") for name, label in outputs]
        input_edges = [(node, job_id) for node in inputs]
        output_edges = [(job_id, f"{job_id}{name}") for name, _ in outputs]

        job_dir = self.rln_dir / job_id
        job_dir.mkdir(parents=True)
        shutil.copy(job_star_path, job_dir / "job.star")
        job_dir.joinpath("note.txt").write_text("")
        _write_blocks(
            job_dir / "job_pipeline.star",
            counter + 1,
            {
                "pipeline_processes": [process],
                "pipeline_nodes": [(n, types[n], "1") for n in inputs] + nodes,
                "pipeline_input_edges": input_edges,
                "pipeline_output_edges": output_edges,
            },
        )

        blocks["pipeline_processes"].append(process)
        blocks["pipeline_nodes"] += nodes
        blocks["pipeline_input_edges"] += input_edges
        blocks["pipeline_output_edges"] += output_edges
        _write_blocks(self.path, counter + 1, blocks)
        shutil.copy(self.path, job_dir / DEFAULT_PIPELINE_STAR)

    def set_status(self, job_id: str, status: str, path: Path | None = None):
        path = path or self.path
        counter, blocks = _read_blocks(path)
        names = [row[0] for row in blocks["pipeline_processes"]]
        idx = names.index(job_id)
        row = blocks["pipeline_processes"][idx]
        blocks["pipeline_processes"][idx] = (*row[:3], status)
        _write_blocks(path, counter, blocks)

    def popen(self, args, **kwargs):
        """Replacement of `subprocess.Popen` for `relion_pipeliner --RunJobs`."""
        assert args[-2] == "--RunJobs"
        job_id = args[-1]
        self.run_calls.append(job_id)
        self.set_status(job_id, "Running")
        # job_pipeline.star is kept "Running" after the job finished
        job_pipeline = self.rln_dir / job_id / "job_pipeline.star"
        self.set_status(job_id, "Running", job_pipeline)

        class _Proc:
            pid = 0

        return _Proc()

    def finish(self, job_id: str):
        """The job finished successfully."""
        _, blocks = _read_blocks(self.path)
        for process, to_node in blocks["pipeline_output_edges"]:
            if process == job_id:
                self.rln_dir.joinpath(to_node).write_text("")
        self.rln_dir.joinpath(job_id, FileNames.EXIT_SUCCESS).touch()
        self.set_status(job_id, "Succeeded")


@pytest.fixture
def in_project(tmp_path: Path, monkeypatch) -> Path:
    # jobs are identified by the paths relative to the project directory
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def relion(in_project: Path, monkeypatch) -> FakeRelionPipeliner:
    fake = FakeRelionPipeliner(in_project)
    monkeypatch.setattr(
        _job_class, "_run_relion_pipeliner_add_job_from_star", fake.add_job_from_star
    )
    monkeypatch.setattr(pipeline_watcher.subprocess, "Popen", fake.popen)
    # The watcher is not started as a new process. `_check_scheduled_jobs` is called
    # instead.
    monkeypatch.setattr(_job_class, "run_watcher_new_process", lambda *_: None)
    return fake


def _default_kwargs(job_cls, **kwargs):
    out = {k: p.default for k, p in job_cls._signature().parameters.items()}
    out.update(kwargs)
    return out


def _start_new_project(ui: MainWindow, rln_dir: Path):
    with file_dialog_response(ui, rln_dir):
        ui.exec_action("himena-relion:start-new-project")
    assert rln_dir.joinpath(DEFAULT_PIPELINE_STAR).exists()


def _create_import_job(rln_dir: Path) -> Path | None:
    return ImportMoviesJob.create_job(
        _cwd=rln_dir, **_default_kwargs(ImportMoviesJob, fn_in_raw="Movies/*.tif")
    )


def _create_motioncorr_job(rln_dir: Path) -> Path | None:
    return MotionCorrOwnJob.create_job(
        _cwd=rln_dir, **_default_kwargs(MotionCorrOwnJob, input_star_mics=MOVIES_STAR)
    )


def _check_scheduled_jobs(rln_dir: Path):
    """What the pipeline watcher does when default_pipeline.star is updated."""
    watcher = pipeline_watcher.RelionPipelineWatcher(rln_dir)
    pipeline = RelionDefaultPipeline.from_pipeline_star(rln_dir / DEFAULT_PIPELINE_STAR)
    watcher._on_job_state_changed(pipeline)


def _read_pipeline(rln_dir: Path) -> RelionPipelineModel:
    return RelionPipelineModel.validate_file(rln_dir / DEFAULT_PIPELINE_STAR)


def _statuses(pipeline: RelionPipelineModel) -> dict[str, str]:
    return dict(zip(pipeline.processes.process_name, pipeline.processes.status_label))


def _input_edges(pipeline: RelionPipelineModel) -> list[tuple[str, str]]:
    return list(zip(pipeline.input_edges.from_node, pipeline.input_edges.process))


def _output_edges(pipeline: RelionPipelineModel) -> list[tuple[str, str]]:
    return list(zip(pipeline.output_edges.process, pipeline.output_edges.to_node))


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
