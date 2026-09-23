"""Functions for running RELION commands installed in WSL from Windows"""

import subprocess
from functools import lru_cache
from pathlib import Path

__all__ = ["wsl_prefix", "wsl_command", "resolve_wsl_env", "is_wsl_path"]

# Variables that describe the shell session rather than the configured environment.
_WSL_ENV_EXCLUDE = frozenset(
    [
        "PWD",
        "OLDPWD",
        "SHLVL",
        "_",
        "PS1",
        "WSL_INTEROP",
        "STARSHIP_SESSION_KEY",
        "LS_COLORS",
    ]
)


def wsl_prefix(cwd: Path | str | None = None) -> list[str]:
    """Command prefix to run a Linux command in WSL (at `cwd` if given)."""
    prefix = ["wsl"]
    if cwd is not None:
        prefix += ["--cd", str(cwd)]
    return [*prefix, "-e"]


def wsl_command(args: list[str], cwd: Path | str | None = None) -> list[str]:
    """Wrap `args` to run in WSL with the environment of the login shell."""
    env = resolve_wsl_env()
    # NOTE: do not quote "k=v" here. Popen quotes arguments containing spaces
    # by itself, and extra quotes would be passed literally to `env`.
    return [*wsl_prefix(cwd), "env", *(f"{k}={v}" for k, v in env.items()), *args]


@lru_cache(maxsize=1)
def resolve_wsl_env() -> dict[str, str]:
    """Resolve environment variables as seen by an interactive login shell in WSL.

    Only the variables added or changed by the shell startup files (.profile,
    .bashrc etc.) are returned. This includes not only PATH and LD_LIBRARY_PATH but
    also variables such as IMOD_DIR, which are required by the IMOD wrapper scripts
    (otherwise they fail with "/bin/realbin/xxx: not found").

    Output of .bashrc (echo, warnings) is ignored by extracting only the text
    between markers.
    """
    _marker_ = "__HIMENA_ENV_MARKER_4-Dp__"
    script = f'printf "{_marker_}"; env -0; printf "{_marker_}"'
    login_env = _parse_env0(
        _run_wsl_capture(["bash", "-lic", script]).split(_marker_)[1]
    )
    base_env = _parse_env0(_run_wsl_capture(["env", "-0"]))
    return {
        k: v
        for k, v in login_env.items()
        if base_env.get(k) != v and k not in _WSL_ENV_EXCLUDE and k.isidentifier()
    }


def is_wsl_path(path: Path | str) -> bool:
    """True if the path is in the WSL file system (such as \\\\wsl.localhost\\...)."""
    return Path(path).drive.startswith(r"\\wsl")


def _run_wsl_capture(args: list[str]) -> str:
    out = subprocess.run(["wsl", "-e", *args], capture_output=True, timeout=30)
    return out.stdout.decode("utf-8", "replace")


def _parse_env0(text: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for item in text.split("\0"):
        if "=" in item:
            k, v = item.split("=", 1)
            env[k] = v
    return env
