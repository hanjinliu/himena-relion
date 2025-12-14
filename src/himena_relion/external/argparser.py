from __future__ import annotations

from pathlib import Path
import sys
import argparse
from typing import Any, Callable, Annotated
import inspect

import starfile

from himena_relion.consts import FileNames
from himena_relion._job import JobDirectory
from himena_relion.external.typemap import parse_string
from himena_relion.external.writers import prep_job_star


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
        self.add_argument("function_id", type=str)
        self.add_argument("--o", type=str)
        self.add_argument("--j", type=int, default=1)
        self.add_argument("--prep_job_star", action="store_true")


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


def pick_function(function_id: str) -> Callable:
    """Pick the function to execute based on function_id."""
    from importlib import import_module
    from runpy import run_path

    if function_id.endswith(".py"):
        ns = run_path(function_id)
        func = ns["main"]
    elif "." in function_id:
        module_name, function_name = function_id.rsplit(".", 1)
        module = import_module(module_name)
        func = getattr(module, function_name)
    else:
        raise ValueError(f"Invalid function_id: {function_id}")
    if not callable(func):
        raise TypeError(f"Function {function_id} is not callable")
    return func


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
    function_id = str(args.pop("function_id"))
    func = pick_function(function_id)
    is_prep_job_star = args.pop("prep_job_star", False)

    if args.get("o", None) is None:
        raise ValueError("Output directory (--o) is required but not given.")
    o_dir = Path(args["o"])

    sig = inspect.signature(func)
    func_args = {}
    for param in sig.parameters.values():
        if param.name in args:
            arg = args.pop(param.name)
            annot = _unwrapped_annotated(param.annotation)
            arg_parsed = parse_string(arg, annot)
            func_args[param.name] = arg_parsed
        elif param.annotation is JobDirectory:
            job_dir = JobDirectory(o_dir)
            func_args[param.name] = job_dir
        elif param.default is param.empty:
            raise ValueError(f"Missing required argument: {param.name}")

    # check if undefined arguments remain
    if unknown := set(args.keys()) - {"o", "j"}:
        func_name = function_id.rsplit(".", 1)[-1]
        raise ValueError(
            f"Unknown arguments for {func_name}: {unknown}. Function signature is "
            f"{func_name}{sig}."
        )

    if is_prep_job_star:
        df = prep_job_star(f"himena-relion {function_id}", **func_args)
        starfile.write(df, o_dir / "job.star")
        return

    # Run the function
    is_generator = inspect.isgeneratorfunction(func)
    if is_generator:
        iterator = func(**func_args)
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
            func(**func_args)
        except Exception:
            o_dir.joinpath(FileNames.EXIT_FAILURE).touch()
    if o_dir.exists():
        o_dir.joinpath(FileNames.EXIT_SUCCESS).touch()
