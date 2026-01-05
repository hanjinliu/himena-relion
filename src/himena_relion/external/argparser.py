from __future__ import annotations

from pathlib import Path
import sys
import argparse
from typing import Any
import inspect

from himena_relion.consts import FileNames
from himena_relion._job_dir import ExternalJobDirectory
from himena_relion.external.job_class import pick_job_class


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
        super().__init__(*args, **kwargs)
        self.add_argument("class_id", type=str)
        self.add_argument("--o", type=str)
        self.add_argument("--j", type=int, default=1)


def parse_argv(argv: list[str] | None = None) -> dict[str, Any]:
    """Parse arguments from sys.argv or given argv list."""
    if argv is None:
        argv = sys.argv[1:]
    parser = RelionExternalArgParser()
    args, unknown = parser.parse_known_args(argv)

    # Parse unknown arguments as additional key-value pairs
    additional_args = {}
    i = 0
    while i < len(unknown):
        arg = unknown[i]
        if arg.startswith("--"):
            key = arg[2:]  # Remove '--' prefix
            if i + 1 < len(unknown) and not unknown[i + 1].startswith("--"):
                # Next item is the value
                additional_args[key] = unknown[i + 1]
                i += 2
            else:
                # Flag without value, set to True
                additional_args[key] = True
                i += 1
        else:
            i += 1

    # Merge additional arguments into parsed args
    result = vars(args)
    result.update(additional_args)
    return result


def run_function(argv: list[str] | None = None) -> None:
    """Run the selected function with parsed arguments."""
    args = parse_argv(argv)
    class_id = str(args.pop("class_id"))
    job_cls = pick_job_class(class_id)

    if args.get("o", None) is None:
        raise ValueError("Output directory (--o) is required but not given.")
    o_dir = Path(args["o"])

    job = job_cls(ExternalJobDirectory(o_dir))
    func_args = job._parse_args(args)

    # check if undefined arguments remain
    if unknown := set(args.keys()) - {"o", "j"}:
        func_name = class_id.rsplit(".", 1)[-1]
        sig = job._signature()
        raise ValueError(
            f"Unknown arguments for {func_name}: {unknown}. Function signature is "
            f"{func_name}{sig}."
        )

    # prepare output nodes in pipeline
    root_rel = job.output_job_dir.path.relative_to(
        job.output_job_dir.relion_project_dir
    )
    with job.output_job_dir.edit_job_pipeline() as pipeline:
        for file_path_rel, label in job.output_nodes():
            pipeline.append_output(root_rel / file_path_rel, label)

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
            if o_dir.joinpath(FileNames.ABORT_NOW).exists():
                raise RuntimeError("Job aborted by user.")
    else:
        try:
            job.run(**func_args)
        except Exception:
            o_dir.joinpath(FileNames.EXIT_FAILURE).touch()
            raise
    if o_dir.exists():
        o_dir.joinpath(FileNames.EXIT_SUCCESS).touch()
