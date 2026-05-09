from himena import MainWindow
from himena.testing import user_string_input_response
import pytest
from himena_relion import _job_dir
from himena_relion.io import _impl
from ._utils import prep_relion_project

def test_updating_job(himena_ui: MainWindow, tmpdir):
    rln_dir = prep_relion_project(tmpdir)
    job_dir = _job_dir.JobDirectory.from_job_star(rln_dir / "MotionCorr/job002/job.star")
    _impl.overwrite_relion_job(himena_ui, job_dir)
    _impl.clone_relion_job(himena_ui, job_dir)
    with user_string_input_response(himena_ui, "alias-0"):
        _impl.set_job_alias(himena_ui, job_dir)

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
