"""Tests of external jobs in a project managed by the emulated `relion_pipeliner`.

The program of the external job (`himena-relion <class ID> --o ...`) is run in the test
process by `FakeRelionPipeliner.run_external`.
"""

from pathlib import Path

import pytest
from himena import MainWindow

from himena_relion._job_dir import ExternalJobDirectory, JobDirectory
from himena_relion.consts import FileNames, Type
from himena_relion.external import RelionExternalJob, pick_job_class, run_function
from himena_relion.external.argparser import parse_argv
from himena_relion.relion5._builtins import ImportMoviesJob
from himena_relion.schemas import RelionPipelineModel

from ._external_jobs import CountLinesJob, TouchJob
from ._fake_relion import (
    FakeRelionPipeliner,
    check_scheduled_jobs,
    default_kwargs,
    input_edges,
    output_edges,
    read_pipeline,
    start_new_project,
    statuses,
)

IMPORT_JOB = "Import/job001/"
MOVIES_STAR = "Import/job001/movies.star"
COUNT_JOB = "External/job002/"
COUNT_ID = "tests._external_jobs:CountLinesJob"


@pytest.fixture
def project(himena_ui: MainWindow, in_project: Path, relion: FakeRelionPipeliner):
    """Project with a finished Import job."""
    start_new_project(himena_ui, in_project)
    ImportMoviesJob.create_job(_cwd=in_project, **default_kwargs(ImportMoviesJob))
    check_scheduled_jobs(in_project)
    relion.finish(IMPORT_JOB)
    in_project.joinpath(MOVIES_STAR).write_text("a\nb\nc\n")
    return in_project


def _status(rln_dir: Path, job_id: str) -> str:
    return statuses(read_pipeline(rln_dir))[job_id]


def test_job_class():
    assert CountLinesJob.import_path() == COUNT_ID
    assert CountLinesJob.command_id() == f"himena-relion:external:{COUNT_ID}"
    assert CountLinesJob.type_label() == "relion.external"
    assert CountLinesJob.job_title() == "Count Lines"
    assert TouchJob.job_title() == "TouchJob"
    assert CountLinesJob.himena_model_type() == "tests-_external_jobs-CountLinesJob"
    assert CountLinesJob.command_palette_title_prefix() == "RELION External:"
    assert list(CountLinesJob._signature().parameters) == [
        "in_mics",
        "repeat",
        "fail",
        "j",
    ]
    assert pick_job_class(COUNT_ID) is CountLinesJob
    assert pick_job_class("tests._external_jobs:NotDefined") is None
    with pytest.raises(ValueError, match="Invalid class_id"):
        pick_job_class("tests._external_jobs.CountLinesJob")
    with pytest.raises(TypeError):
        pick_job_class("pathlib:Path")


def test_parse_argv():
    args = parse_argv(
        [COUNT_ID, "--o", "External/job002/", "--in_mics", "a.star", "--fail", "--j", "4"]
    )
    assert args == {
        "class_id": COUNT_ID,
        "o": "External/job002/",
        "j": 4,
        "in_mics": "a.star",
        "fail": True,
    }
    args = parse_argv([COUNT_ID, "ignored", "--repeat", "3", "--fail"])
    assert args == {"class_id": COUNT_ID, "o": None, "j": 1, "repeat": "3", "fail": True}

def _parse_cli(job_cls: type[RelionExternalJob], *argv: str) -> dict:
    args = parse_argv(["class_id", "--o", "External/job002/", *argv])
    args.pop("class_id")
    return job_cls._parse_args(args)

def test_parse_empty_values():
    """RELION passes an empty value as `--param`, without the value."""
    from himena_relion.relion5.extensions.volume_tools.jobs import ManualMaskCreation

    # list[float] and float | None
    args = _parse_cli(ManualMaskCreation, "--other_binning", "--pre_lowpass")
    assert args["other_binning"] == []
    assert args["pre_lowpass"] is None
    args = _parse_cli(ManualMaskCreation, "--other_binning", "2,4", "--pre_lowpass")
    assert args["other_binning"] == [2.0, 4.0]
    assert args["pre_lowpass"] is None
    # str
    assert _parse_cli(TouchJob, "--in_parts", "a.star", "--name")["name"] == ""
    # a bool flag given by hand still means True
    args = _parse_cli(CountLinesJob, "--in_mics", "a.star", "--fail")
    assert args["fail"] is True
    # int cannot be empty
    with pytest.raises(ValueError, match="'repeat' \\(int\\) cannot be empty"):
        _parse_cli(CountLinesJob, "--in_mics", "a.star", "--repeat")


def test_run_external_job(himena_ui: MainWindow, project: Path, relion):
    job_path = CountLinesJob.create_job(
        _cwd=project, **default_kwargs(CountLinesJob, in_mics=MOVIES_STAR, repeat=2, j=3)
    )
    assert job_path == project / COUNT_JOB
    pipeline = read_pipeline(project)
    assert list(pipeline.processes.type_label) == [
        "relion.import.movies",
        "relion.external",
    ]
    assert input_edges(pipeline) == [(MOVIES_STAR, COUNT_JOB)]

    # the job directory is dispatched to the job class
    job_dir = JobDirectory.from_job_star(job_path / "job.star")
    assert isinstance(job_dir, ExternalJobDirectory)
    assert job_dir.job_import_path() == COUNT_ID
    assert job_dir._to_job_class() is CountLinesJob
    assert job_dir.job_title() == "Count Lines"
    model_type = f"{Type.RELION_JOB}.tests-_external_jobs-CountLinesJob"
    assert job_dir.himena_model_type() == model_type
    params = job_dir.get_job_params_as_dict()
    assert params["fn_exe"] == f"himena-relion {COUNT_ID}"
    assert params["in_mic"] == MOVIES_STAR
    assert (params["repeat"], params["fail"], params["nr_threads"]) == ("2", "No", "3")
    kwargs = CountLinesJob._parse_args(CountLinesJob.normalize_kwargs_inv(**params))
    assert kwargs == {"in_mics": MOVIES_STAR, "repeat": 2, "fail": False, "j": 3}

    # run
    check_scheduled_jobs(project)
    assert relion.run_calls == [IMPORT_JOB, COUNT_JOB]
    assert relion.run_external(COUNT_JOB) is None
    assert _status(project, COUNT_JOB) == "Succeeded"
    assert job_path.joinpath("count.txt").read_text() == "6"
    assert job_path.joinpath("progress.txt").read_text() == "1"
    # the output node is added by the job
    job_pipeline = RelionPipelineModel.validate_file(job_dir.job_pipeline())
    assert input_edges(job_pipeline) == [(MOVIES_STAR, COUNT_JOB)]
    assert output_edges(job_pipeline) == [(COUNT_JOB, "External/job002/count.txt")]
    assert list(job_pipeline.nodes.type_label) == [
        "MicrographMoviesData.star.relion",
        "LogFile.txt.himena.count",
    ]


def test_external_job_failed_and_aborted(himena_ui: MainWindow, project: Path, relion):
    job_path = CountLinesJob.create_job(
        _cwd=project,
        **default_kwargs(CountLinesJob, in_mics=MOVIES_STAR, repeat=3, fail=True),
    )
    job_dir = JobDirectory.from_job_star(job_path / "job.star")
    check_scheduled_jobs(project)
    error = relion.run_external(COUNT_JOB)
    assert isinstance(error, ValueError) and str(error) == "failed as requested"
    assert _status(project, COUNT_JOB) == "Failed"
    assert job_path.joinpath(FileNames.EXIT_FAILURE).exists()
    assert not job_path.joinpath("count.txt").exists()

    # overwrite the job and abort it while running
    CountLinesJob(job_dir).edit_and_run_job(
        **default_kwargs(CountLinesJob, in_mics=MOVIES_STAR, repeat=3)
    )
    assert _status(project, COUNT_JOB) == "Scheduled"
    assert not job_path.joinpath(FileNames.EXIT_FAILURE).exists()
    assert job_dir.get_job_params_as_dict()["fail"] == "No"
    check_scheduled_jobs(project)
    job_path.joinpath(FileNames.ABORT_NOW).touch()
    error = relion.run_external(COUNT_JOB)
    assert isinstance(error, RuntimeError) and "aborted" in str(error)
    assert _status(project, COUNT_JOB) == "Aborted"
    assert job_path.joinpath("progress.txt").read_text() == "0"
    assert job_path.joinpath(FileNames.EXIT_ABORTED).exists()
    assert not job_path.joinpath(FileNames.ABORT_NOW).exists()


def test_overwriting_external_job_keeps_input_edges(
    himena_ui: MainWindow, project: Path, relion
):
    job_path = CountLinesJob.create_job(
        _cwd=project, **default_kwargs(CountLinesJob, in_mics=MOVIES_STAR)
    )
    job_dir = JobDirectory.from_job_star(job_path / "job.star")
    assert input_edges(read_pipeline(project)) == [(MOVIES_STAR, COUNT_JOB)]
    CountLinesJob(job_dir).edit_and_run_job(
        **default_kwargs(CountLinesJob, in_mics=MOVIES_STAR, repeat=2)
    )
    assert input_edges(read_pipeline(project)) == [(MOVIES_STAR, COUNT_JOB)]


def test_external_job_not_generator(himena_ui: MainWindow, project: Path, relion):
    particles = "Extract/job099/particles.star"
    mask = "MaskCreate/job098/mask.mrc"
    job_path = TouchJob.create_job(
        _cwd=project, **default_kwargs(TouchJob, in_parts=particles, in_mask=mask)
    )
    assert job_path is None  # the inputs are not ready
    job_id = "External/job002/"
    job_path = project / job_id
    pipeline = read_pipeline(project)
    assert input_edges(pipeline) == [(particles, job_id), (mask, job_id)]
    job_dir = JobDirectory.from_job_star(job_path / "job.star")
    assert job_dir._to_job_class() is TouchJob
    assert TouchJob(job_dir).input_edges(in_parts=particles, in_mask=mask) == [
        particles,
        mask,
    ]

    assert relion.run_external(job_id) is None
    assert job_path.joinpath("touched.txt").exists()
    assert job_path.joinpath(FileNames.EXIT_SUCCESS).exists()
    assert output_edges(RelionPipelineModel.validate_file(job_dir.job_pipeline())) == []

    # failed
    job_path.joinpath(FileNames.EXIT_SUCCESS).unlink()
    with pytest.raises(ValueError, match="name must be given"):
        run_function(
            ["tests._external_jobs:TouchJob", "--o", job_id, "--in_parts", particles]
            + ["--name", ""]
        )
    assert job_path.joinpath(FileNames.EXIT_FAILURE).exists()
    assert not job_path.joinpath(FileNames.EXIT_SUCCESS).exists()


def test_invalid_command_lines(himena_ui: MainWindow, project: Path, relion):
    CountLinesJob.create_job(
        _cwd=project, **default_kwargs(CountLinesJob, in_mics=MOVIES_STAR)
    )
    with pytest.raises(ValueError, match="Output directory"):
        run_function([COUNT_ID, "--in_mics", MOVIES_STAR])
    with pytest.raises(ValueError, match="External job not found"):
        run_function(["tests._external_jobs:NotDefined", "--o", COUNT_JOB])
    with pytest.raises(ValueError, match="Unknown arguments"):
        run_function(
            [COUNT_ID, "--o", COUNT_JOB, "--in_mics", MOVIES_STAR, "--unknown", "1"]
        )
    with pytest.raises(ValueError, match="Missing required argument: in_mics"):
        run_function([COUNT_ID, "--o", COUNT_JOB])
    assert not project.joinpath(COUNT_JOB, FileNames.EXIT_SUCCESS).exists()


def test_single_file_job(himena_ui: MainWindow, project: Path, relion):
    """Job classes defined in a .py file, which is not a module."""
    py_file = project / "my_job.py"
    py_file.write_text(
        "from himena_relion.external import RelionExternalJob\n\n"
        "class CopyJob(RelionExternalJob):\n"
        "    def output_nodes(self):\n"
        "        return [('copied.star', 'MicrographMoviesData.star')]\n\n"
        "    def run(self, in_movies):\n"
        "        job_dir = self.output_job_dir\n"
        "        text = job_dir.resolve_path(in_movies).read_text()\n"
        "        job_dir.path.joinpath('copied.star').write_text(text)\n"
    )
    # NOTE: absolute paths of Windows cannot be used because of the drive letter
    class_id = "my_job.py:CopyJob"
    job_cls = pick_job_class(class_id)
    assert issubclass(job_cls, RelionExternalJob)
    assert job_cls.import_path() == class_id
    assert pick_job_class(class_id) is job_cls  # the file is not run again

    job_path = job_cls.create_job(
        _cwd=project, **default_kwargs(job_cls, in_movies=MOVIES_STAR)
    )
    job_dir = JobDirectory.from_job_star(job_path / "job.star")
    assert job_dir._to_job_class() is job_cls
    assert job_dir.get_job_param("in_mov") == MOVIES_STAR
    check_scheduled_jobs(project)
    assert relion.run_external(COUNT_JOB) is None
    assert job_path.joinpath("copied.star").read_text() == "a\nb\nc\n"
    assert _status(project, COUNT_JOB) == "Succeeded"


def test_external_job_without_class(tmp_path: Path):
    """External jobs that are not himena-relion jobs."""
    job_path = tmp_path / "External" / "job001"
    job_path.mkdir(parents=True)
    job_path.joinpath("job.star").write_text(
        "data_job\n\n"
        "_rlnJobTypeLabel             relion.external\n"
        "_rlnJobIsContinue                       0\n"
        "_rlnJobIsTomo                           0\n\n"
        "data_joboptions_values\n\nloop_\n"
        "_rlnJobOptionVariable #1\n_rlnJobOptionValue #2\n"
        "fn_exe my_program\nin_mic mics.star\n"
        "param1_label threshold\nparam1_value 0.5\n"
        "param2_label \"\"\nparam2_value \"\"\n"
    )
    job_dir = JobDirectory.from_job_star(job_path / "job.star")
    assert isinstance(job_dir, ExternalJobDirectory)
    assert job_dir.job_import_path() is None
    assert job_dir._to_job_class() is None
    assert job_dir.himena_model_type() == f"{Type.RELION_JOB}.unknown"
    assert job_dir.get_job_params_as_dict() == {
        "fn_exe": "my_program",
        "in_mic": "mics.star",
        "threshold": "0.5",
    }
