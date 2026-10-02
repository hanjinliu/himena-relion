import sys
from pathlib import Path, PureWindowsPath

import pytest

from himena_relion import _configs
from himena_relion._wsl import is_wsl_path, to_wsl_path, wsl_prefix


@pytest.mark.parametrize(
    "path, expected",
    [
        (r"\\wsl.localhost\Ubuntu\home\user\a.mrc", "/home/user/a.mrc"),
        (r"\\wsl$\Ubuntu\home\user", "/home/user"),
        ("//wsl.localhost/Ubuntu/data/a b.mrc", "/data/a b.mrc"),
        (r"\\wsl.localhost\Ubuntu", "/"),
        (r"C:\Users\user\a.mrc", "/mnt/c/Users/user/a.mrc"),
        ("D:/data", "/mnt/d/data"),
        ("Class3D/job001/run_class001.mrc", "Class3D/job001/run_class001.mrc"),
    ],
)
def test_to_wsl_path(path: str, expected: str):
    assert to_wsl_path(path) == expected


def test_is_wsl_path():
    assert is_wsl_path(r"\\wsl.localhost\Ubuntu\home")
    assert is_wsl_path(PureWindowsPath(r"\\wsl$\Ubuntu\home"))
    assert not is_wsl_path(r"C:\Users")
    assert not is_wsl_path("/home/user")


@pytest.fixture
def launched(monkeypatch: pytest.MonkeyPatch) -> list[tuple[list[str], dict]]:
    """Capture the subprocess calls in `_configs` instead of running them."""
    calls = []
    monkeypatch.setattr(
        _configs, "wsl_command", lambda args, cwd=None: [*wsl_prefix(cwd), *args]
    )
    monkeypatch.setattr(
        _configs.subprocess, "Popen", lambda args, **kw: calls.append((args, kw))
    )
    monkeypatch.setattr(
        _configs.subprocess, "run", lambda args, **kw: calls.append((args, kw))
    )
    return calls


def test_open_in_external_app_wsl(launched, monkeypatch: pytest.MonkeyPatch):
    found = {"chimerax": "/usr/bin/chimerax"}
    monkeypatch.setattr(_configs, "wsl_which", found.get)
    config = _configs.RelionConfig(chimera="chimerax")
    monkeypatch.setattr(_configs, "_get_himena_relion_config", lambda: config)

    path = PureWindowsPath(r"\\wsl.localhost\Ubuntu\home\u\proj\Refine3D\job001\a.mrc")
    _configs.open_in_chimerax(path)
    assert launched[-1][0] == [
        "wsl", "-e", "setsid", "-w", "/usr/bin/chimerax", "/home/u/proj/Refine3D/job001/a.mrc"
    ]
    _configs.open_in_3dmod(path)
    args, kwargs = launched[-1]
    assert args[-4:] == ["setsid", "-w", "3dmod", "/home/u/proj/Refine3D/job001/a.mrc"]
    assert kwargs["cwd"] is None  # given by `wsl --cd` instead
    if sys.platform == "win32":
        assert args[:3] == ["wsl", "--cd", "/home/u/proj/Refine3D/job001"]
    config.chimera = "not_installed"
    with pytest.raises(RuntimeError):
        _configs.open_in_chimerax(path)


def test_open_in_imod_command_cwd(launched, tmpdir):
    edf = Path(tmpdir, "TS_01", "TS_01.edf")
    _configs.open_in_imod_command(edf, "etomo")
    args, kwargs = launched[-1]
    assert args == ["etomo", str(edf)]
    assert kwargs["cwd"] == edf.parent
