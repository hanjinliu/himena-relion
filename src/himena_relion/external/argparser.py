from __future__ import annotations

from pathlib import Path
import sys
import argparse
from typing import Any
import inspect

from himena_relion.consts import FileNames
from himena_relion._job_dir import ExternalJobDirectory
from himena_relion.external._other_args import iter_options
from himena_relion.external.job_class import RelionExternalContinue, pick_job_class


class RelionExternalArgParser(argparse.ArgumentParser):
    """Argument parser for RELION external job types.

    This argument parser allows to run python function as a RELION external job type.
    Command works like:

    ```bash
    himena-relion himena_relion.relion5_tomo.extensions.erase_gold.run_erase_gold \
        --in_mics External/job_find/tomograms.star --o External/job_erase \
        --seed 441442
    ```

    and from RELION GUI, you can set the command by
    ```
    (Input)
    External executable: himena-relion himena_relion.relion5_tomo.extensions.erase_gold.run_erase_gold
    Input micrographs: External/job_find/tomograms.star
    (Params)
    seed: 441442
    ```
    """

    def __init__(self, *args, **kwargs):
        # job parameters such as `--p` must not be taken as abbreviations of the
        # arguments below (e.g. `--pipeline_control`).
        kwargs.setdefault("allow_abbrev", False)
        super().__init__(*args, **kwargs)
        self.add_argument("class_id", type=str)
        self.add_argument("--o", type=str)
        self.add_argument("--j", type=int, default=1)
        # RELION appends `--pipeline_control <job dir>` to any command that contains
        # "relion_" anywhere, e.g. in the class ID `my_relion_plugin.jobs:MyJob` or in
        # a file path (`--pipeline-control` for Python programs).
        self.add_argument(
            "--pipeline_control",
            "--pipeline-control",
            dest="pipeline_control",
            type=str,
            default=argparse.SUPPRESS,
        )


def parse_argv(argv: list[str] | None = None) -> dict[str, Any]:
    """Parse arguments from sys.argv or given argv list."""
    if argv is None:
        argv = sys.argv[1:]
    parser = RelionExternalArgParser()
    args, unknown = parser.parse_known_args(argv)

    # Parse unknown arguments as additional key-value pairs. These are given by the
    # parameter slots and "Additional arguments" (`other_args`) of the job. A flag
    # without value is set to True.
    additional_args = {
        key: True if value is None else value for key, value in iter_options(unknown)
    }

    # Merge additional arguments into parsed args
    result = vars(args)
    result.update(additional_args)
    return result


def run_function(argv: list[str] | None = None) -> None:
    """Run the selected function with parsed arguments."""
    args = parse_argv(argv)
    class_id = str(args.pop("class_id"))  # ID to determine job class
    # RELION looks for the RELION_JOB_EXIT_* files in the pipeline control directory,
    # which is the job directory given by `--o` for External jobs. The files are
    # written there below, so the argument is not needed.
    args.pop("pipeline_control", None)
    job_cls = pick_job_class(class_id)

    if args.get("o", None) is None:
        raise ValueError("Output directory (--o) is required but not given.")
    if job_cls is None:
        raise ValueError(f"External job not found for class_id: {class_id}")
    o_dir = Path(args["o"])

    job_dir = ExternalJobDirectory(o_dir)
    job = job_cls(job_dir)
    func_args = job._parse_args(args)

    # check if undefined arguments remain
    known = {"o", "j"}
    if isinstance(job, RelionExternalContinue):
        # the command line of a continued job has all the parameters of the original
        # job, and `run` only uses some of them.
        known.update(job.original_class._signature().parameters)
    if unknown := set(args.keys()) - known:
        func_name = class_id.rsplit(".", 1)[-1]
        sig = job._signature()
        raise ValueError(
            f"Unknown arguments for {func_name}: {unknown}. Function signature is "
            f"{func_name}{sig}."
        )

    # prepare output nodes in pipeline
    root_rel = job.output_job_dir.path.relative_to(job_dir.relion_project_dir)

    # FIXME: At the moment the job_pipeline.star is updated, Job is already running and
    # the default_pipeline.star does not include all the output nodes.
    with job.output_job_dir.edit_job_pipeline() as pipeline:
        for file_path_rel, label in job.output_nodes():
            pipeline.append_output(root_rel / file_path_rel, label)

    # Log version
    job._log_job_version_info()

    # Run the function
    is_generator = inspect.isgeneratorfunction(job.run)
    if is_generator:
        iterator = job.run(**func_args)
        while True:
            try:
                next(iterator)
            except StopIteration:
                break
            except Exception:
                o_dir.joinpath(FileNames.EXIT_FAILURE).touch()
                raise
            if (abort_now := o_dir.joinpath(FileNames.ABORT_NOW)).exists():
                o_dir.joinpath(FileNames.EXIT_ABORTED).touch()
                abort_now.unlink()
                raise RuntimeError("Job aborted by user.")
    else:
        try:
            job.run(**func_args)
        except Exception:
            o_dir.joinpath(FileNames.EXIT_FAILURE).touch()
            raise
    if o_dir.exists():
        o_dir.joinpath(FileNames.EXIT_SUCCESS).touch()
