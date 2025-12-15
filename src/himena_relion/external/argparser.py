from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import argparse
from typing import Any, Annotated
import inspect
from enum import IntEnum

import starfile

from himena_relion.consts import FileNames
from himena_relion._job import ExternalJobDirectory
from himena_relion.external.typemap import parse_string
from himena_relion.external.writers import prep_job_star
from himena_relion.external.job_class import RelionExternalJob


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
        self.add_argument("--prep_job_star_for_pipeliner")


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


def pick_job_class(class_id: str) -> type[RelionExternalJob]:
    """Pick the function to execute based on class_id."""
    from importlib import import_module
    from runpy import run_path

    if class_id.count(":") != 1:
        raise ValueError(f"Invalid class_id: {class_id}")
    class_file_path, class_name = class_id.split(":", 1)
    if class_file_path.endswith(".py"):
        ns = run_path(class_file_path)
        job_cls = ns[class_name]
    else:
        module = import_module(class_file_path)
        job_cls = getattr(module, class_name)
    if not issubclass(job_cls, RelionExternalJob):
        raise TypeError(f"Function {class_id} is not callable")
    return job_cls


def _unwrapped_annotated(annot: Any) -> Any:
    origin = getattr(annot, "__origin__", None)
    if origin is Annotated:
        args = annot.__args__
        base_type = args[0]
        return base_type
    else:
        return annot


def run_function(argv: list[str] | None = None) -> None:
    """Run the selected function with parsed arguments."""
    args = parse_argv(argv)
    class_id = str(args.pop("class_id"))
    job_cls = pick_job_class(class_id)
    prep_job_star_enum = PrepJobStarEnum(args.pop("prep_job_star_for_pipeliner", 0))

    if args.get("o", None) is None:
        raise ValueError("Output directory (--o) is required but not given.")
    o_dir = Path(args["o"])

    job = job_cls(ExternalJobDirectory(o_dir))
    sig = inspect.signature(job.run)
    func_args = {}
    for param in sig.parameters.values():
        if param.name in args:
            arg = args.pop(param.name)
            annot = _unwrapped_annotated(param.annotation)
            arg_parsed = parse_string(arg, annot)
            func_args[param.name] = arg_parsed
        elif param.default is param.empty:
            raise ValueError(f"Missing required argument: {param.name}")

    # check if undefined arguments remain
    if unknown := set(args.keys()) - {"o", "j"}:
        func_name = class_id.rsplit(".", 1)[-1]
        raise ValueError(
            f"Unknown arguments for {func_name}: {unknown}. Function signature is "
            f"{func_name}{sig}."
        )

    if prep_job_star_enum > 0:
        df = prep_job_star(f"himena-relion {class_id}", **func_args)
        starfile.write(df, o_dir / "job.star")
        if prep_job_star_enum is PrepJobStarEnum.PREP_ONLY:
            pass
        elif prep_job_star_enum is PrepJobStarEnum.PREP_AND_ADD:
            subprocess.run(
                ["relion_pipeliner", "--addJobFromStar", str(o_dir / "job.star")],
                check=True,
            )
        return

    # prepare output nodes in pipeline
    root_rel = job.output_job_dir.path.relative_to(
        job.output_job_dir.relion_project_dir
    )
    with job.output_job_dir.edit_job_pipeline() as pipeline:
        for file_path_rel, label in job.output_job_dir:
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
            except Exception as e:
                o_dir.joinpath(FileNames.EXIT_FAILURE).touch()
                raise e
            if o_dir.joinpath(FileNames.ABORT_NOW).exists():
                raise RuntimeError("Job aborted by user.")
    else:
        try:
            job.run(**func_args)
        except Exception:
            o_dir.joinpath(FileNames.EXIT_FAILURE).touch()
    if o_dir.exists():
        o_dir.joinpath(FileNames.EXIT_SUCCESS).touch()


class PrepJobStarEnum(IntEnum):
    NONE = 0
    PREP_ONLY = 1
    PREP_AND_ADD = 2
