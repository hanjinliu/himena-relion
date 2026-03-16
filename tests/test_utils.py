from typing import Annotated

import pytest

from himena_relion import _utils

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
