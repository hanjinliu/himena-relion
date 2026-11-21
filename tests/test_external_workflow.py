"""Tests of external jobs in a project managed by the emulated `relion_pipeliner`.

The program of the external job (`himena-relion <class ID> --o ...`) is run in the test
process by `FakeRelionPipeliner.run_external`.
"""

from pathlib import Path

import pytest
from himena import MainWindow
from himena.plugins import when_reader_used
from himena.workflow import LocalReaderMethod

from himena_relion._job_dir import ExternalJobDirectory, JobDirectory
from himena_relion.consts import FileNames, Type
from himena_relion.external import (
    RelionExternalContinue,
    RelionExternalJob,
    pick_job_class,
    run_function,
)
from himena_relion.external.argparser import parse_argv
from himena_relion.relion5._builtins import ImportMoviesJob
from himena_relion.schemas import JobStarModel, RelionPipelineModel

from ._external_jobs import (
    AccumulateJob,
    AddToTotal,
    CountLinesJob,
    MultiplyTotal,
    TouchJob,
)
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


@pytest.mark.parametrize("flag", ["--pipeline_control", "--pipeline-control"])
def test_parse_argv_pipeline_control(flag: str):
    """RELION appends `--pipeline_control <job dir>` to commands with "relion_"."""
    args = parse_argv([COUNT_ID, "--o", COUNT_JOB, "--p", "3", flag, COUNT_JOB])
    assert args == {
        "class_id": COUNT_ID,
        "o": COUNT_JOB,
        "j": 1,
        "p": "3",  # not an abbreviation of --pipeline_control
        "pipeline_control": COUNT_JOB,
    }


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


@pytest.mark.parametrize(
    "filename",
    [
        "my_job.py",
        # RELION appends `--pipeline_control` because the command contains "relion_"
        "relion_job.py",
    ],
)
def test_single_file_job(himena_ui: MainWindow, project: Path, relion, filename: str):
    """Job classes defined in a .py file, which is not a module."""
    py_file = project / filename
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
    class_id = f"{filename}:CopyJob"
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


ACC_JOB = "External/job002/"
ACC_ID = "tests._external_jobs:AccumulateJob"
ADD_ID = "tests._external_jobs:AddToTotal"
MULTIPLY_ID = "tests._external_jobs:MultiplyTotal"


def _write_job_options(job_dir: JobDirectory, **options: str):
    """Change the job options in job.star."""
    job_star = JobStarModel.validate_file(job_dir.job_star())
    values = job_star.joboptions_values.to_dict()
    values.update(options)
    job_star.joboptions_values = JobStarModel.Options(
        variable=list(values), value=list(values.values())
    ).dataframe
    job_star.to_star_dict().write(job_dir.job_star(), newline="\n")


def _param_slots(options: dict[str, str]) -> dict[str, str]:
    """Label -> value of the parameter slots (param1_label etc.) in job.star."""
    out = {}
    for ith in range(1, 11):
        if label := options.get(f"param{ith}_label", ""):
            out[label] = options[f"param{ith}_value"]
    return out


def _suggested_contexts(ui: MainWindow, job_dir: JobDirectory) -> dict[str, dict]:
    """Command ID -> context of the commands suggested from the job window."""
    model_type = job_dir.himena_model_type()
    meth = LocalReaderMethod(output_model_type=model_type, path=job_dir.path)
    reg = when_reader_used(model_type)._registry
    return {
        s.command_id: s.user_context(ui, meth)
        for s in reg.iter_suggestion(model_type, meth)
    }


def test_continue_job_class():
    from himena_relion._job_class import RelionJob

    assert AddToTotal._is_continue_job()
    assert not AccumulateJob._is_continue_job()
    assert AddToTotal.command_id() == f"himena-relion:external:{ADD_ID}"
    assert MultiplyTotal.command_id() == f"himena-relion:external:{MULTIPLY_ID}"
    assert AddToTotal.command_palette_title_prefix() == "Continue -"
    assert AddToTotal.job_title() == "AccumulateJob"
    assert MultiplyTotal.job_title() == "Multiply Total"
    assert AddToTotal.himena_model_type() == AccumulateJob.himena_model_type()
    assert AddToTotal.type_label() == "relion.external"
    assert pick_job_class(ADD_ID) is AddToTotal
    # continue jobs are not registered as new jobs
    new_jobs = {cmd.command_id for cmd in RelionJob.__relion_job_commands__}
    assert AccumulateJob.command_id() in new_jobs
    assert AddToTotal.command_id() not in new_jobs


def test_continue_external_job(himena_ui: MainWindow, project: Path, relion):
    from himena_relion import _job_class
    from himena_relion._job_class import _JOB_DIR_ARGS_NAME

    job_path = AccumulateJob.create_job(
        _cwd=project,
        **default_kwargs(AccumulateJob, in_mics=MOVIES_STAR, value=2, label="x", j=3),
    )
    job_dir = JobDirectory.from_job_star(job_path / "job.star")
    model_type = job_dir.himena_model_type()
    assert model_type == f"{Type.RELION_JOB}.tests-_external_jobs-AccumulateJob"
    check_scheduled_jobs(project)
    assert relion.run_external(ACC_JOB) is None
    assert job_path.joinpath("total.txt").read_text() == "2"
    assert _status(project, ACC_JOB) == "Succeeded"

    # all the continue jobs are suggested from the job window
    contexts = _suggested_contexts(himena_ui, job_dir)
    context = contexts[AddToTotal.command_id()]
    assert context[_JOB_DIR_ARGS_NAME].path == job_dir.path
    assert MultiplyTotal.command_id() in contexts

    # the queue settings are not the parameters, and are kept
    _write_job_options(job_dir, qsub="my_qsub")

    # the suggested command shows the scheduler to continue the job
    himena_ui.exec_action(AddToTotal.command_id(), user_context=context)
    scheduler = _job_class.scheduler_widget(himena_ui)
    assert scheduler._current_job_cls is AddToTotal
    # `repeat` is not a parameter of the original job, so the default is used
    assert scheduler.get_parameters() == {
        "in_mics": MOVIES_STAR,
        "value": 2,
        "repeat": 1,
    }

    # continue from the scheduler
    scheduler = AddToTotal._show_scheduler_widget_for_continue(
        himena_ui, {**context, "value": 5, "repeat": 2}
    )
    assert scheduler.get_parameters() == {
        "in_mics": MOVIES_STAR,
        "value": 5,
        "repeat": 2,
    }
    # the input nodes cannot be changed
    assert not scheduler._job_param_widget._mgui_widgets["in_mics"].enabled
    assert scheduler._job_param_widget._mgui_widgets["value"].enabled
    assert scheduler._exec_btn.text() == "Continue Job"
    assert "Continue" in scheduler._title_label.text()
    scheduler.preview_job_star()
    preview = JobStarModel.validate_text(himena_ui.current_model.value)
    assert preview.job.job_is_continue == 1
    assert preview.joboptions_values.to_dict()["fn_exe"] == f"himena-relion {ADD_ID}"
    scheduler._exec_btn.click()

    job_star = JobStarModel.validate_file(job_dir.job_star())
    assert job_star.job.job_is_continue == 1
    assert job_star.job.job_type_label == "relion.external"
    assert job_star.joboptions_values.to_dict()["qsub"] == "my_qsub"
    params = job_dir.get_job_params_as_dict()
    assert params["fn_exe"] == f"himena-relion {ADD_ID}"
    assert params["in_mic"] == MOVIES_STAR
    assert (params["value"], params["label"], params["nr_threads"]) == ("5", "x", "3")
    assert params["repeat"] == "2"
    assert _status(project, ACC_JOB) == "Scheduled"
    assert not job_path.joinpath(FileNames.EXIT_SUCCESS).exists()
    assert input_edges(read_pipeline(project)) == [(MOVIES_STAR, ACC_JOB)]
    # the continued job is still a job of the original class
    assert job_dir.job_import_path() == ADD_ID
    assert job_dir._to_job_class() is AccumulateJob
    assert job_dir.himena_model_type() == model_type
    assert job_dir.job_title() == "AccumulateJob"

    # RELION runs the program of the continue job
    check_scheduled_jobs(project)
    assert relion.run_calls == [IMPORT_JOB, ACC_JOB, ACC_JOB]
    assert relion.run_external(ACC_JOB) is None
    assert job_path.joinpath("total.txt").read_text() == "12"
    assert job_path.joinpath("continued_with.txt").read_text() == MOVIES_STAR
    assert _status(project, ACC_JOB) == "Succeeded"
    # the output node is not added twice
    job_pipeline = RelionPipelineModel.validate_file(job_dir.job_pipeline())
    assert output_edges(job_pipeline) == [(ACC_JOB, f"{ACC_JOB}total.txt")]

    # the value of `repeat` of the last continue is used
    scheduler = AddToTotal._show_scheduler_widget_for_continue(himena_ui, context)
    assert scheduler.get_parameters()["repeat"] == 2
    scheduler.clear_content()

    # continue by another continue job
    assert MultiplyTotal.command_id() in _suggested_contexts(himena_ui, job_dir)
    MultiplyTotal(job_dir).continue_job(value=3)
    assert job_dir.get_job_param("fn_exe") == f"himena-relion {MULTIPLY_ID}"
    assert job_dir.get_job_param("value") == "3"
    # `repeat` is not passed to MultiplyTotal
    assert "repeat" not in job_dir.get_job_params_as_dict()
    check_scheduled_jobs(project)
    assert relion.run_external(ACC_JOB) is None
    assert job_path.joinpath("total.txt").read_text() == "36"
    # "Continue" in RELION GUI runs the same program again
    assert relion.run_external(ACC_JOB) is None
    assert job_path.joinpath("total.txt").read_text() == "108"

    # the input nodes are kept, and `repeat` is the default as it was not used last
    job_star = AddToTotal(job_dir).make_job_star(in_mics="Job/job009/a.star", value=1)
    options = job_star.joboptions_values.to_dict()
    assert options["in_mic"] == MOVIES_STAR
    assert _param_slots(options) == {"value": "1", "label": "x", "repeat": "1"}
    # the command line has the parameters of the original job
    with pytest.raises(ValueError, match="Unknown arguments"):
        run_function(
            [ADD_ID, "--o", ACC_JOB, "--in_mics", MOVIES_STAR, "--label", "x"]
            + ["--unknown", "1"]
        )

    # overwriting the job runs the original job again
    AccumulateJob(job_dir).edit_and_run_job(
        **default_kwargs(AccumulateJob, in_mics=MOVIES_STAR, value=4)
    )
    job_star = JobStarModel.validate_file(job_dir.job_star())
    assert job_star.job.job_is_continue == 0
    assert job_dir.get_job_param("fn_exe") == f"himena-relion {ACC_ID}"
    assert "repeat" not in job_dir.get_job_params_as_dict()


def test_continue_mode_needs_continue_job(
    himena_ui: MainWindow, project: Path, relion
):
    from himena_relion._widgets._job_edit import ContinueMode

    job_path = CountLinesJob.create_job(
        _cwd=project, **default_kwargs(CountLinesJob, in_mics=MOVIES_STAR)
    )
    job_dir = JobDirectory.from_job_star(job_path / "job.star")
    scheduler = CountLinesJob._show_scheduler_widget(himena_ui, {})
    scheduler._mode = ContinueMode(job_dir)
    with pytest.raises(RuntimeError, match="Cannot continue"):
        scheduler._mode.exec(scheduler)


def test_invalid_continue_job_classes():
    with pytest.raises(TypeError, match="original_class must be"):

        class NoOriginal(RelionExternalContinue):
            def run(self, value: int = 1):
                pass

    with pytest.raises(TypeError, match="original_class must be"):

        class ContinueOfContinue(RelionExternalContinue):
            original_class = AddToTotal

            def run(self, value: int = 1):
                pass

    # input nodes cannot be added
    with pytest.raises(TypeError, match="'in_parts' of NewInput.run"):

        class NewInput(RelionExternalContinue):
            original_class = AccumulateJob

            def run(self, in_parts, value: int = 1):
                pass
