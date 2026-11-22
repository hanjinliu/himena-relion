"""Job parameters passed by "Additional arguments" (`other_args`) of External jobs.

RELION's External job has only 10 parameter slots (`param1_label` to `param10_label`).
The parameters that do not fit in the slots are written to `other_args`, which RELION
appends to the command line as is (`RelionJob::getCommandsExternalJob`):

    <fn_exe> --o <job dir> --in_mics <file> ... --<label> <value> ...
        --j <n> <other_args>

The command line is run by `system()`, so `other_args` is split by the shell.
"""

from __future__ import annotations

import re
import shlex
from typing import Iterable, Iterator

NUM_PARAM_SLOTS = 10


def iter_options(tokens: Iterable[str]) -> Iterator[tuple[str, str | None]]:
    """Iterate over `(key, value)` of `--key value` in the command line tokens.

    The value is None for a flag without value. Tokens that are neither an option nor
    its value are skipped.
    """
    tokens = list(tokens)
    i = 0
    while i < len(tokens):
        arg = tokens[i]
        if arg.startswith("--"):
            key = arg[2:]
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                yield key, tokens[i + 1]
                i += 2
            else:
                yield key, None
                i += 1
        else:
            i += 1


def quote_for_shell(value: str) -> str:
    """Escape the special characters of the shell with backslashes.

    Quotation marks are not used for quoting (unlike `shlex.quote`), because they are
    not read correctly from the quoted values in STAR files, such as
    `"--name 'a b'"`.
    """
    return _UNSAFE_CHARS.sub(r"\\\1", value)


_UNSAFE_CHARS = re.compile(r"([^\w@%+=:,./-])")


def format_other_args(params: dict[str, str]) -> str:
    """Format the parameters as `--key value` to be passed by `other_args`.

    An empty value is written as `--key` without value, which is the same as what
    RELION passes for an empty parameter slot.
    """
    parts = []
    for key, value in params.items():
        parts.append(f"--{key}")
        if value != "":
            parts.append(quote_for_shell(value))
    return " ".join(parts)


def parse_other_args(other_args: str) -> dict[str, str]:
    """Parse the `--key value` parameters in `other_args`.

    A flag without value is parsed as an empty string, as the empty parameter slots.
    """
    try:
        tokens = shlex.split(other_args)
    except ValueError:  # such as unclosed quotation edited by hand
        return {}
    return {key: value or "" for key, value in iter_options(tokens)}
