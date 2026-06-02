from pathlib import Path
from typing import Annotated

import pytest

from himena_relion import _utils
from himena_relion._version import RelionVersion
from himena_relion.schemas import RelionPipelineModel
from ._utils import prep_relion_project

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

def test_lock(tmpdir):
    tmpdir = Path(tmpdir)
    pipeline_star = tmpdir / "default_pipeline.star"
    pipeline_star.write_text("pipeline_general\n_rlnPipeLineJobCounter 5\n")
    with _utils.open_with_lock(pipeline_star) as f:
        assert tmpdir.joinpath(".relion_lock").exists()
        f.read()  # make sure the file is readable
        f.seek(0)
        f.write("pipeline_general\n_rlnPipeLineJobCounter 6\n")
    assert not tmpdir.joinpath(".relion_lock").exists()

    with _utils.open_with_lock(pipeline_star) as f:
        assert tmpdir.joinpath(".relion_lock").exists()
        with pytest.raises(_utils.RelionPipelineLockError):
            with _utils.open_with_lock(pipeline_star):
                pass
        assert tmpdir.joinpath(".relion_lock").exists()
        f.read()  # make sure the file is readable
        f.seek(0)
        f.write("pipeline_general\n_rlnPipeLineJobCounter 6\n")
    assert not tmpdir.joinpath(".relion_lock").exists()

    with pytest.raises(ValueError):
        with _utils.open_with_lock(pipeline_star):
            raise ValueError
    assert not tmpdir.joinpath(".relion_lock").exists()

def test_replace_input_edges(tmpdir):
    # Import/job001/tilt_series.star MotionCorr/job002/
    path = Path(tmpdir) / "default_pipeline.star"

    rln_dir = prep_relion_project(tmpdir)
    star_path = rln_dir / "default_pipeline.star"
    assert star_path.exists()
    assert "Import/job001/tilt_series.star MotionCorr/job002/" in star_path.read_text()
    assert "MotionCorr/job002/corrected_tilt_series.star CtfFind/job003/" in star_path.read_text()
    with _utils.open_with_lock(path) as f:
        _utils.replace_input_edges(f, "MotionCorr/job002/")
    assert "Import/job001/tilt_series.star\tMotionCorr/job002/" not in star_path.read_text()
    assert "MotionCorr/job002/corrected_tilt_series.star\tCtfFind/job003/" in star_path.read_text()

JOB_PIPELINE_TXT = """data_pipeline_general
_rlnPipeLineJobCounter                       2

data_pipeline_processes
loop_
_rlnPipeLineProcessName #1
_rlnPipeLineProcessAlias #2
_rlnPipeLineProcessTypeLabel #3
_rlnPipeLineProcessStatusLabel #4
CtfFind/job003/       None relion.ctffind.ctffind4    Running

data_pipeline_nodes
loop_
_rlnPipeLineNodeName #1
_rlnPipeLineNodeTypeLabel #2
_rlnPipeLineNodeTypeLabelDepth #3
MotionCorr/job002/corrected_tilt_series.star TomogramGroupMetadata.star.relion 1
CtfFind/job003/tilt_series_ctf.star TomogramGroupMetadata.star.relion.tomo.ctffind 1

data_pipeline_input_edges
loop_
_rlnPipeLineEdgeFromNode #1
_rlnPipeLineEdgeProcess #2
MotionCorr/job002/corrected_tilt_series.star CtfFind/job003/

data_pipeline_output_edges
loop_
_rlnPipeLineEdgeProcess #1
_rlnPipeLineEdgeToNode #2
CtfFind/job003/ CtfFind/job003/tilt_series_ctf.star
"""

def test_replace_input_edges_with_default_pipeline(tmpdir):
    default_pipeline = Path(tmpdir) / "default_pipeline.star"

    rln_dir = prep_relion_project(tmpdir)
    star_path = rln_dir / "default_pipeline.star"
    assert star_path.exists()

    pipeline_path = Path(tmpdir) / "job_pipeline.star"
    pipeline_path.write_text(JOB_PIPELINE_TXT)
    with pipeline_path.open("r+") as f:
        _utils.replace_input_edges(
            f,
            "CtfFind/job003/",
            new_inputs=["Import/job001/tilt_series.star"],
            default_pipeline=default_pipeline,
        )

    p1 = RelionPipelineModel.validate_file(pipeline_path)
    assert p1.nodes.dataframe.shape[0] == 2
    assert list(p1.nodes.name) == [
        "Import/job001/tilt_series.star",
        "CtfFind/job003/tilt_series_ctf.star",
    ]
