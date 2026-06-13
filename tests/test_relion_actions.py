from pathlib import Path
import numpy as np
import pytest
import mrcfile
from himena import MainWindow
from himena.testing import user_string_input_response, choose_one_dialog_response
from himena_relion import _job_dir
from himena_relion.io import _impl
from ._utils import prep_relion_project

def test_set_alias(himena_ui: MainWindow, tmpdir):
    rln_dir = prep_relion_project(tmpdir)
    job_dir = _job_dir.JobDirectory.from_job_star(rln_dir / "MotionCorr/job002/job.star")
    _impl.overwrite_relion_job(himena_ui, job_dir)
    _impl.clone_relion_job(himena_ui, job_dir)
    with user_string_input_response(himena_ui, "alias-0"):
        _impl.set_job_alias(himena_ui, job_dir)
    assert rln_dir.joinpath("MotionCorr/alias-0").is_symlink()
    assert "alias-0" in job_dir.path.joinpath("job_pipeline.star").read_text()

    # update alias to another name
    with user_string_input_response(himena_ui, "alias-1"):
        _impl.set_job_alias(himena_ui, job_dir)
    assert not rln_dir.joinpath("MotionCorr/alias-0").exists()
    assert rln_dir.joinpath("MotionCorr/alias-1").is_symlink()
    assert "alias-0" not in job_dir.path.joinpath("job_pipeline.star").read_text()
    assert "alias-1" in job_dir.path.joinpath("job_pipeline.star").read_text()

    # cannot start with "job"
    with pytest.raises(ValueError):
        with user_string_input_response(himena_ui, "job-xyz"):
            _impl.set_job_alias(himena_ui, job_dir)
    # invalid characters
    with pytest.raises(ValueError):
        with user_string_input_response(himena_ui, "a*+b"):
            _impl.set_job_alias(himena_ui, job_dir)

def test_mark_as(tmpdir):
    rln_dir = prep_relion_project(tmpdir)
    job_dir = _job_dir.JobDirectory.from_job_star(rln_dir / "MotionCorr/job002/job.star")
    _impl.mark_as_failed(job_dir)
    _impl.mark_as_finished(job_dir)

def test_delete_files_subtomo(
    himena_ui: MainWindow,
    tmpdir,
    jobs_dir_tomo,
):
    job_dir = prep_relion_project(tmpdir).joinpath("Extract/job099")
    job_dir.mkdir(parents=True, exist_ok=True)
    job_dir.joinpath("Subtomograms").mkdir(parents=True, exist_ok=True)
    for i in range(3):
        subdir = job_dir.joinpath(f"Subtomograms/TS_{i}")
        subdir.mkdir(parents=True, exist_ok=True)
        for j in range(4):
            with mrcfile.new(subdir.joinpath(f"TS_{i}_{j}.mrc")) as mrc:
                mrc.set_data(np.zeros((3, 10, 10), dtype=np.float32))

    job_star_text = Path(jobs_dir_tomo).joinpath("Extract/job001/job.star").read_text()
    job_dir.joinpath("job.star").write_text(job_star_text)
    himena_ui.read_file(job_dir.joinpath("job.star"))
    with choose_one_dialog_response(himena_ui, True):
        himena_ui.exec_action("himena-relion:delete-all-subtomos")
    assert job_dir.joinpath("Subtomograms").exists()
    assert list(job_dir.joinpath("Subtomograms").iterdir()) == []

# def test_delete_files_tomo(
#     himena_ui: MainWindow,
#     tmpdir,
#     jobs_dir_tomo,
# ):
#     job_dir = prep_relion_project(tmpdir).joinpath("Tomogram/job099")
#     job_dir.mkdir(parents=True, exist_ok=True)
#     job_dir.joinpath("tomograms").mkdir(parents=True, exist_ok=True)
#     for i in range(3):
#         with mrcfile.new(job_dir.joinpath(f"tomograms/rec_TS_{i}.mrc")) as mrc:
#             mrc.set_data(np.zeros((10, 10, 10), dtype=np.float32))

#     job_star_text = Path(jobs_dir_tomo).joinpath("Tomogram/job001/job.star").read_text()
#     job_dir.joinpath("job.star").write_text(job_star_text)
#     himena_ui.read_file(job_dir.joinpath("job.star"))
#     assert len(list(job_dir.joinpath("tomograms").iterdir())) == 3
#     with choose_one_dialog_response(himena_ui, True):
#         himena_ui.exec_action("himena-relion:delete-all-tomos")
#     assert job_dir.joinpath("tomograms").exists()
#     assert list(job_dir.joinpath("tomograms").iterdir()) == []
