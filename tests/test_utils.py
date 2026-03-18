from typing import Annotated

import pytest

from himena_relion import _utils
from himena_relion._version import RelionVersion

def test_util_functions():
    mat = _utils.make_tilt_projection_mat(12)
    assert mat.shape == (3, 3)

    type0 = _utils.unwrap_annotated(Annotated[int, {"label": "a"}])
    assert type0 is int

@pytest.mark.parametrize(
    "input_, expected",
    [
        ("Class2D/job001", "Class2D/job001/"),
        ("Class2D/job001/", "Class2D/job001/"),
    ]
)
def test_normalize_job_id(input_: str, expected: str):
    assert _utils.normalize_job_id(input_) == expected

def test_relion_version():
    ver = RelionVersion(5, 0, 1)
    assert str(ver) == "5.0.1"
    assert ver < (6,)
    assert ver < (5, 1)
    assert ver <= (5, 0, 1)
    assert ver <= (5, 1, 0)
    assert ver > (4, 9)
    assert ver >= (5, 0, 1)

def test_get_relion_version_info(monkeypatch: pytest.MonkeyPatch):
    from himena_relion import _version

    monkeypatch.setattr(
        _version,
        "relion_version",
        lambda: "RELION version: 5.0.0-commit-85db73\nPrecision: BASE=double\n"
    )

    info = _version.relion_version_info()
    assert info.version == RelionVersion(5, 0, 0)
    assert info.commit == "85db73"
