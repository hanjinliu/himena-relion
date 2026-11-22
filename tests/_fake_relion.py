"""Emulation of `relion_pipeliner`, which edits default_pipeline.star as RELION does.

Note that RELION does not write the blocks without any rows, so that a new project does
not have `pipeline_input_edges` until a job with inputs is added.

Use the `relion` fixture (see conftest.py) to schedule jobs by `RelionJob.create_job` in
the `in_project` directory. Import and MotionCorr jobs have the output nodes as in
RELION. For the other job types, the outputs are given by `FakeRelionPipeliner.outputs`
and the inputs are what `RelionJob.input_edges` returns. External jobs are run in the
test process by `FakeRelionPipeliner.run_external`.
"""

import re
import shlex
import shutil
import subprocess
from pathlib import Path

from himena import MainWindow
from himena.testing import file_dialog_response
from starfile_rs import read_star

from himena_relion import pipeline_watcher
from himena_relion._job_class import RelionJob, iter_relion_jobs
from himena_relion._pipeline import RelionDefaultPipeline
from himena_relion._utils import unwrap_annotated
from himena_relion.consts import DEFAULT_PIPELINE_STAR, FileNames
from himena_relion.external import run_function
from himena_relion.schemas import JobStarModel, RelionPipelineModel


_POPEN = subprocess.Popen  # the original one, before the `relion` fixture replaces it
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
# The second part of the type label -> directory name, if not simply capitalized
_DIRNAMES = {
    "motioncorr": "MotionCorr",
    "ctffind": "CtfFind",
    "manualpick": "ManualPick",
    "autopick": "AutoPick",
    "class2d": "Class2D",
    "class3d": "Class3D",
    "refine3d": "Refine3D",
    "initialmodel": "InitialModel",
    "maskcreate": "MaskCreate",
    "postprocess": "PostProcess",
    "ctfrefine": "CtfRefine",
    "importtomo": "Import",
    "reconstructparticletomo": "Reconstruct",
    "ctfrefinetomo": "CtfRefine",
    "framealigntomo": "Polish",
    "pseudosubtomo": "Extract",
}
# The input parameters of external jobs -> the arguments given to the program
_EXTERNAL_INPUTS = [
    ("in_mov", "--in_movies"),
    ("in_mic", "--in_mics"),
    ("in_part", "--in_parts"),
    ("in_coords", "--in_coords"),
    ("in_3dref", "--in_3dref"),
    ("in_mask", "--in_mask"),
]
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


def _find_job_class(job_star: JobStarModel) -> "type[RelionJob]":
    """The job class of the job.star, to know which parameters are the inputs."""
    label = job_star.job.job_type_label
    is_tomo = bool(job_star.job.job_is_tomo)
    params = job_star.joboptions_values.to_dict()
    classes = [
        cls
        for cls in iter_relion_jobs()
        if cls.type_label() == label and cls.job_is_tomo() == is_tomo
    ]
    assert classes, f"No job class for {label}"
    for cls in classes:
        if cls.param_matches(params):
            return cls
    return classes[0]


def _node_label(filename: str) -> str:
    return f"ProcessData.{filename.rsplit('.', 1)[-1]}.relion"


def read_blocks(path: Path) -> tuple[int, dict[str, list[tuple[str, ...]]]]:
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


def write_blocks(path: Path, counter: int, blocks: dict[str, list[tuple[str, ...]]]):
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
        # type label -> [(output file, node type label)] of the jobs not in _JOB_SPECS
        self.outputs: dict[str, list[tuple[str, str]]] = {}
        # file name -> node type label of the inputs that are not the output of jobs
        self.input_labels: dict[str, str] = {}

    @property
    def path(self) -> Path:
        return self.rln_dir / DEFAULT_PIPELINE_STAR

    def _job_spec(self, job_star: JobStarModel, job_star_path: Path):
        """Directory name, [(output file, node type label)] and the input files."""
        label = job_star.job.job_type_label
        params = job_star.joboptions_values.to_dict()
        if label in _JOB_SPECS:
            dirname, outputs, input_keys = _JOB_SPECS[label]
            return dirname, outputs, [params[k] for k in input_keys if params[k] != ""]
        if label == "relion.external":
            # the output nodes are added by the program itself
            inputs = [params[k] for k, _ in _EXTERNAL_INPUTS if params[k] != ""]
            return "External", [], inputs
        # Other job types: the inputs are what himena-relion considers as the inputs,
        # and the outputs are given by `self.outputs`.
        job_cls = _find_job_class(job_star)
        key = label.removeprefix("relion.").split(".")[0]
        dirname = _DIRNAMES.get(key, key.title())
        edges = [str(edge).strip() for edge in job_cls(None).input_edges(**params)]
        inputs = [edge for edge in dict.fromkeys(edges) if edge != ""]
        return dirname, self.outputs.get(label, []), inputs

    def add_job_from_star(self, job_star_path: Path, cwd: Path, *, alias=None):
        assert Path(cwd) == self.rln_dir
        job_star = JobStarModel.validate_file(job_star_path)
        dirname, outputs, inputs = self._job_spec(job_star, Path(job_star_path))
        counter, blocks = read_blocks(self.path)
        job_id = f"{dirname}/job{counter:03d}/"
        types = {row[0]: row[1] for row in blocks["pipeline_nodes"]}
        # files that are not the output of any jobs are also registered as nodes
        new_inputs = [
            (n, self.input_labels.get(Path(n).name, _node_label(n)), "1")
            for n in inputs
            if n not in types
        ]
        types.update({row[0]: row[1] for row in new_inputs})

        process = (job_id, "None", job_star.job.job_type_label, "Scheduled")
        nodes = [(f"{job_id}{name}", label, "1") for name, label in outputs]
        input_edges = [(node, job_id) for node in inputs]
        output_edges = [(job_id, f"{job_id}{name}") for name, _ in outputs]

        job_dir = self.rln_dir / job_id
        job_dir.mkdir(parents=True)
        shutil.copy(job_star_path, job_dir / "job.star")
        job_dir.joinpath("note.txt").write_text("")
        write_blocks(
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
        blocks["pipeline_nodes"] += new_inputs + nodes
        blocks["pipeline_input_edges"] += input_edges
        blocks["pipeline_output_edges"] += output_edges
        write_blocks(self.path, counter + 1, blocks)
        shutil.copy(self.path, job_dir / DEFAULT_PIPELINE_STAR)

    def set_status(self, job_id: str, status: str, path: Path | None = None):
        path = path or self.path
        counter, blocks = read_blocks(path)
        names = [row[0] for row in blocks["pipeline_processes"]]
        idx = names.index(job_id)
        row = blocks["pipeline_processes"][idx]
        blocks["pipeline_processes"][idx] = (*row[:3], status)
        write_blocks(path, counter, blocks)

    def popen(self, args, *other_args, **kwargs):
        """Replacement of `subprocess.Popen` for `relion_pipeliner --RunJobs`."""
        if not (isinstance(args, list) and args[-2:-1] == ["--RunJobs"]):
            # `subprocess.Popen` is replaced for all the modules. Other programs (e.g.
            # those matplotlib runs on Linux to find fonts) are run as usual.
            return _POPEN(args, *other_args, **kwargs)
        job_id = args[-1]
        self.run_calls.append(job_id)
        self.set_status(job_id, "Running")
        # job_pipeline.star is kept "Running" after the job finished
        job_pipeline = self.rln_dir / job_id / "job_pipeline.star"
        self.set_status(job_id, "Running", job_pipeline)

        class _Proc:
            pid = 0

            def poll(self):
                return 0

        return _Proc()

    def run_external(self, job_id: str) -> Exception | None:
        """Run the program of the external job, which must be `himena-relion`.

        The command is run in this process. The exception is returned if failed.
        """
        job_dir = self.rln_dir / job_id
        params = JobStarModel.validate_file(job_dir / "job.star")
        params = params.joboptions_values.to_dict()
        exe, class_id = params["fn_exe"].split()
        assert exe == "himena-relion"
        argv = [class_id, "--o", job_id]
        for key, flag in _EXTERNAL_INPUTS:
            if params[key] != "":
                argv += [flag, params[key]]
        for i in range(1, 11):
            if label := params[f"param{i}_label"]:
                argv.append(f"--{label}")
                if value := params[f"param{i}_value"]:
                    argv.append(value)
        argv += ["--j", params["nr_threads"]]
        # "Additional arguments" are appended as is, and split by the shell
        argv += shlex.split(params["other_args"])
        # RELION (`RelionJob::prepareFinalCommand`) appends this to any command that
        # contains "relion_" anywhere.
        if "relion_" in " ".join([params["fn_exe"], *argv]):
            argv += ["--pipeline_control", job_id]
        try:
            run_function(argv)
        except Exception as e:
            error = e
        else:
            error = None
        # RELION updates the status when it finds the files
        for filename, status in [
            (FileNames.EXIT_SUCCESS, "Succeeded"),
            (FileNames.EXIT_FAILURE, "Failed"),
            (FileNames.EXIT_ABORTED, "Aborted"),
        ]:
            if job_dir.joinpath(filename).exists():
                self.set_status(job_id, status)
        return error

    def finish(self, job_id: str, *, files: tuple[str, ...] = ()):
        """The job finished successfully. `files` are also written in the job."""
        for name in files:
            self.rln_dir.joinpath(job_id, name).write_text("")
        _, blocks = read_blocks(self.path)
        for process, to_node in blocks["pipeline_output_edges"]:
            if process == job_id:
                self.rln_dir.joinpath(to_node).write_text("")
        self.rln_dir.joinpath(job_id, FileNames.EXIT_SUCCESS).touch()
        self.set_status(job_id, "Succeeded")


def default_kwargs(job_cls: "type[RelionJob]", **kwargs):
    """The default parameters of the job class, updated by `kwargs`."""
    out = {}
    for name, param in job_cls._signature().parameters.items():
        out[name] = param.default
        if param.default is None and unwrap_annotated(param.annotation) is dict:
            out[name] = {}  # composite widgets return a dict
    out.update(kwargs)
    return out


def start_new_project(ui: MainWindow, rln_dir: Path):
    with file_dialog_response(ui, rln_dir):
        ui.exec_action("himena-relion:start-new-project")
    assert rln_dir.joinpath(DEFAULT_PIPELINE_STAR).exists()


def check_scheduled_jobs(rln_dir: Path):
    """What the pipeline watcher does when default_pipeline.star is updated."""
    watcher = pipeline_watcher.RelionPipelineWatcher(rln_dir)
    pipeline = RelionDefaultPipeline.from_pipeline_star(rln_dir / DEFAULT_PIPELINE_STAR)
    watcher._on_job_state_changed(pipeline)


def read_pipeline(rln_dir: Path) -> RelionPipelineModel:
    return RelionPipelineModel.validate_file(rln_dir / DEFAULT_PIPELINE_STAR)


def statuses(pipeline: RelionPipelineModel) -> dict[str, str]:
    return dict(zip(pipeline.processes.process_name, pipeline.processes.status_label))


def input_edges(pipeline: RelionPipelineModel) -> list[tuple[str, str]]:
    return list(zip(pipeline.input_edges.from_node, pipeline.input_edges.process))


def output_edges(pipeline: RelionPipelineModel) -> list[tuple[str, str]]:
    return list(zip(pipeline.output_edges.process, pipeline.output_edges.to_node))
