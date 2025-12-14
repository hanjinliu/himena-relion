from __future__ import annotations

import sys
import argparse
from typing import Any, Callable, Annotated
import inspect
from himena_relion.external.typemap import parse_string


class RelionExternalArgParser(argparse.ArgumentParser):
    """Argument parser for RELION external job types.

    This argument parser allows to run python function as a RELION external job type.
    Command works like:

    ```bash
    himena-relion himena_relion.relion5_tomo.extensions.erase_gold.run_erase_gold \
        --in_mics TestEraseGold/job_find/tomograms.star --o TestEraseGold/job_erase \
        --seed 441442
    ```
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument("function_id", type=str)
        for yyy in ["movies", "mics", "parts", "coords", "3dref", "mask"]:
            self.add_argument(f"--in_{yyy}", type=str)
        self.add_argument("--o", type=str)
        self.add_argument("--j", type=int)


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


def run_function() -> None:
    """Run the selected function with parsed arguments."""
    args = parse_argv()
    function_id = args.pop("function_id")
    func = pick_function(function_id)

    sig = inspect.signature(func)
    func_args = {}
    for param in sig.parameters.values():
        if param.name in args:
            arg = args[param.name]
            annot = _unwrapped_annotated(param.annotation)
            arg = parse_string(arg, annot)
            func_args[param.name] = arg
        elif param.default is param.empty:
            raise ValueError(f"Missing required argument: {param.name}")

    print(func_args)
    # Run the function
    func(**func_args)
