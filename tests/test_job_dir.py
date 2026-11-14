"""Tests of `JobDirectory` and the functions reading the job outputs."""

import shutil
from pathlib import Path

import numpy as np
import pytest

from himena_relion import _job_dir
from himena_relion._job_dir import JobDirectory
from himena_relion.consts import JOB_ID_MAP, RelionJobState, Type

from ._utils import JOBS_DIR_SPA, JOBS_DIR_TOMO

_MODEL_STAR = """
data_model_general

_rlnReferenceDimensionality 3

data_model_groups

loop_
_rlnGroupNumber #1
_rlnGroupName #2
_rlnGroupNrParticles #3
1 group_01 {0}
2 group_02 {1}
"""
_PARTICLES_STAR = """
data_optics

loop_
_rlnOpticsGroup #1
_rlnOpticsGroupName #2
1 optics1

data_particles

loop_
_rlnTomoName #1
_rlnOpticsGroup #2
TS_01 1
TS_01 1
TS_02 1
"""


def _copy_job(rln_dir: Path, src: Path, job_id: str) -> JobDirectory:
    """Copy job.star of the test data to make a job directory in the project."""
    path = rln_dir / job_id
    path.mkdir(parents=True)
    shutil.copy(src / "job.star", path / "job.star")
    return JobDirectory.from_job_star(path / "job.star")


def _write_star(path: Path, text: str) -> Path:
    path.write_text(text, newline="\n")
    return path


def test_invalid_paths(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        JobDirectory(tmp_path / "Refine3D" / "job001")
    file = tmp_path / "file.txt"
    file.write_text("")
    with pytest.raises(NotADirectoryError):
        JobDirectory(file)
    with pytest.raises(ValueError, match="Expected job.star"):
        JobDirectory.from_job_star(file)
    with pytest.raises(FileNotFoundError):
        JobDirectory.from_job_star(tmp_path / "job.star")


def test_job_directory_basics(tmp_path: Path):
    job_dir = _copy_job(tmp_path, JOBS_DIR_SPA / "Refine3D" / "job001", "Refine3D/job012")
    assert isinstance(job_dir, _job_dir.Refine3DJobDirectory)
    assert repr(job_dir) == f"Refine3DJobDirectory(path={job_dir.path.as_posix()})"
    assert job_dir.job_number == "012"
    assert job_dir.job_normal_id() == "Refine3D/job012/"
    assert job_dir.relion_project_dir == tmp_path.resolve()
    assert job_dir.job_type_label() == "relion.refine3d"
    assert job_dir.job_title() == JOB_ID_MAP["relion.refine3d"]
    assert job_dir.himena_model_type() == f"{Type.RELION_JOB}.relion.refine3d"
    assert not job_dir.is_tomo()
    assert job_dir.get_job_param("ini_high") == "60"
    assert job_dir.get_job_param("not_a_parameter", "default") == "default"

    # paths relative to the project
    job_dir.path.joinpath("run_data.star").write_text("")
    relative = Path("Refine3D/job012/run_data.star")
    assert job_dir.resolve_path(relative) == job_dir.path / "run_data.star"
    assert job_dir.resolve_path(job_dir.path) == job_dir.path
    assert job_dir.resolve_path("Refine3D/job099/x.star") == Path("Refine3D/job099/x.star")
    assert job_dir.make_relative_path(job_dir.path / "run_data.star") == relative
    outside = tmp_path.parent.resolve() / "outside.star"
    assert job_dir.make_relative_path(outside) == outside

    # state files
    assert job_dir.can_abort()
    assert job_dir.state() is RelionJobState.RUNNING
    for filename, state in [
        ("RELION_JOB_ABORT_NOW", RelionJobState.ABORT_NOW),
        ("RELION_JOB_EXIT_ABORTED", RelionJobState.EXIT_ABORTED),
        ("RELION_JOB_EXIT_FAILURE", RelionJobState.EXIT_FAILURE),
        ("RELION_JOB_EXIT_SUCCESS", RelionJobState.EXIT_SUCCESS),
    ]:
        job_dir.path.joinpath(filename).touch()
        assert job_dir.state() is state
        assert not job_dir.can_abort()

    # files in the subdirectories
    sub = job_dir.path / "sub"
    sub.mkdir()
    sub.joinpath("a.mrc").write_text("")
    sub.joinpath("b.star").write_text("")
    assert [p.name for p in job_dir.glob_in_subdirs("*.mrc")] == ["a.mrc"]

    # everything other than the job definition is removed
    job_dir.path.joinpath("note.txt").write_text("note")
    job_dir.clear_job()
    assert sorted(p.name for p in job_dir.path.iterdir()) == ["job.star", "note.txt"]
    assert job_dir.state() is RelionJobState.RUNNING

    # job.star is needed to know the job type
    job_dir.job_star().unlink()
    assert job_dir._to_job_class() is None
    assert job_dir.job_title() == "Unknown"


def test_job_number_of_alias(tmp_path: Path):
    job_dir = _copy_job(tmp_path, JOBS_DIR_SPA / "Refine3D" / "job001", "Refine3D/final")
    assert job_dir.job_number == "final"


def test_trashed_job_directory(tmp_path: Path):
    path = tmp_path / "Trash" / "Refine3D" / "job012"
    path.mkdir(parents=True)
    assert _job_dir.TrashedJobDirectory(path).relion_project_dir == tmp_path.resolve()


def test_tilt_series_and_tomograms(tmp_path: Path):
    path = tmp_path / "Tomograms" / "job005"
    for sub, names in [
        ("tilt_series", ["TS_01.star", "TS_02.star", "TS_01.txt"]),
        ("tomograms", ["rec_TS_01.mrc", "rec_TS_01.txt"]),
    ]:
        path.joinpath(sub).mkdir(parents=True)
        for name in names:
            path.joinpath(sub, name).write_text("")
    ts_job = _job_dir.HasTiltSeriesJobDirectory(path)
    assert sorted(p.name for p in ts_job.iter_tilt_series_path()) == [
        "TS_01.star",
        "TS_02.star",
    ]
    tomo_job = _job_dir.HasTomogramsJobDirectory(path)
    assert [p.name for p in tomo_job.iter_tomograms()] == ["rec_TS_01.mrc"]


def test_tomogram_info():
    info = _job_dir.TomogramInfo.from_dict(
        {
            "rlnTomoName": "TS_01",
            "rlnTomoTiltSeriesPixelSize": 1.5,
            "rlnTomoTomogramBinning": 4.0,
            "rlnTomoSizeX": 400,
            "rlnTomoSizeY": 300,
            "rlnTomoSizeZ": 200,
            "rlnTomoReconstructedTomogramHalf1": "Tomograms/job005/half1.mrc",
            "rlnTomoReconstructedTomogramHalf2": "Tomograms/job005/half2.mrc",
        }
    )
    assert info.is_halfset_reconstruction
    assert info.tomo_pixel_size == 6.0
    assert info.tomo_shape == (200, 300, 400)
    info = _job_dir.TomogramInfo.from_dict(
        {"rlnTomoName": "TS_01", "rlnTomoReconstructedTomogramDenoised": "d.mrc"}
    )
    assert info.reconstructed_tomogram == [Path("d.mrc")]
    assert not info.is_halfset_reconstruction
    assert info.tomo_pixel_size == -1.0


def test_refine3d_results(tmp_path: Path):
    job_dir = _copy_job(tmp_path, JOBS_DIR_SPA / "Refine3D" / "job001", "Refine3D/job012")
    assert isinstance(job_dir, _job_dir.Refine3DJobDirectory)
    assert job_dir.num_iters() == -1
    assert _job_dir.try_get_particle_number(job_dir) == -1
    for niter in [0, 3]:
        job_dir.path.joinpath(f"run_it{niter:03d}_data.star").write_text("")
    assert job_dir.num_iters() == 3

    # particles are split into two half sets
    _write_star(job_dir.path / "run_it003_half1_model.star", _MODEL_STAR.format(10, 20))
    assert _job_dir.try_get_particle_number(job_dir) == -1
    _write_star(job_dir.path / "run_it003_half2_model.star", _MODEL_STAR.format(11, 21))
    assert _job_dir.try_get_particle_number(job_dir) == 62
    job_dir.path.joinpath("run_it003_half2_model.star").write_text("broken")
    assert _job_dir.try_get_particle_number(job_dir) == -1

    # angular distribution
    bild = (
        ".color 0.5 0 1\n"
        ".cylinder 10 20 30 12 24 36 0.5\n"
        ".color 1 0 0\n"
        ".cylinder 0 0 0 2 4 6 1\n"
    )
    job_dir.path.joinpath("run_class001_angdist.bild").write_text(bild)
    job_dir.path.joinpath("run_it003_half1_class001_angdist.bild").write_text(bild)
    assert job_dir.get_result(2).angdist(1, 2.0) == []
    for result in [job_dir.get_final_result(), job_dir.get_result(3)]:
        tubes = result.angdist(1, 2.0)
        assert len(tubes) == 2
        np.testing.assert_allclose(tubes[0].start, [5, 10, 15])
        np.testing.assert_allclose(tubes[0].end, [6, 12, 18])
        assert tubes[0].radius == 0.25
        assert tubes[0].color == (0.5, 0.0, 1.0)
        assert tubes[1].radius == 0.5

    # PostProcess: the number of particles of the parent job
    job_dir.path.joinpath("run_it003_half2_model.star").unlink()
    _write_star(job_dir.path / "run_it003_half2_model.star", _MODEL_STAR.format(1, 2))
    post = _copy_job(tmp_path, JOBS_DIR_SPA / "PostProcess" / "job001", "PostProcess/job013")
    assert _job_dir.try_get_particle_number(post) == -1  # the parent is not found
    text = post.job_star().read_text()
    fn_in = post.get_job_param("fn_in")
    assert fn_in != ""
    post.job_star().write_text(
        text.replace(fn_in, "Refine3D/job012/run_half1_class001_unfil.mrc")
    )
    assert _job_dir.try_get_particle_number(post) == -1  # the half map is not found
    job_dir.path.joinpath("run_half1_class001_unfil.mrc").write_text("")
    assert _job_dir.try_get_particle_number(post) == 33


def test_class3d_results(tmp_path: Path):
    job_dir = _copy_job(tmp_path, JOBS_DIR_SPA / "Class3D" / "job001", "Class3D/job010")
    assert isinstance(job_dir, _job_dir.Class3DJobDirectory)
    assert job_dir.num_iters() == -1
    assert _job_dir.num_classes(job_dir) == 0
    for name in [
        "run_it000_class001.mrc",
        "run_it025_class001.mrc",
        "run_it025_class004.mrc",
        "run_it025_classXXX.mrc",
    ]:
        job_dir.path.joinpath(name).write_text("")
    assert _job_dir.num_classes(job_dir) == 4
    _write_star(job_dir.path / "run_it025_model.star", _MODEL_STAR.format(5, 7))
    job_dir.path.joinpath("run_itXXX_model.star").write_text("")
    assert job_dir.num_iters() == 25
    assert _job_dir.try_get_particle_number(job_dir) in (12, -1)  # either file is read
    job_dir.path.joinpath("run_itXXX_model.star").unlink()
    assert _job_dir.try_get_particle_number(job_dir) == 12

    result = job_dir.get_result(25)
    assert result.class_map(7) == (None, 1.0)
    assert result.angdist(1, 1.0) == []  # no alignment


def test_particle_number_of_tomo_reconstruct(tmp_path: Path):
    job_dir = _copy_job(
        tmp_path, JOBS_DIR_TOMO / "Reconstruct" / "job001", "Reconstruct/job020"
    )
    assert job_dir.job_type_label() == "relion.reconstructparticletomo"
    # the input files are not found
    assert _job_dir.try_get_particle_number(job_dir) == -1

    extract = tmp_path / "Extract" / "job019"
    extract.mkdir(parents=True)
    _write_star(extract / "particles.star", _PARTICLES_STAR)
    _write_star(
        extract / "optimisation_set.star",
        "\ndata_\n\n"
        "_rlnTomoParticlesFile Extract/job019/particles.star\n"
        "_rlnTomoTomogramsFile Tomograms/job005/tomograms.star\n",
    )
    params = job_dir.get_job_params_as_dict()
    text = job_dir.job_star().read_text()
    for key in ["in_optimisation", "in_particles"]:
        if params[key] != "":
            text = text.replace(params[key], '""')
    job_dir.job_star().write_text(text)
    assert _job_dir.try_get_particle_number(job_dir) is None  # no inputs

    def _set_param(key: str, value: str):
        lines = []
        for line in job_dir.job_star().read_text().splitlines():
            if line.split()[:1] == [key]:
                line = f"{key} {value}"
            lines.append(line)
        job_dir.job_star().write_text("\n".join(lines) + "\n", newline="\n")

    _set_param("in_particles", "Extract/job019/particles.star")
    assert _job_dir.try_get_particle_number(job_dir) == 3
    _set_param("in_optimisation", "Extract/job019/optimisation_set.star")
    _set_param("in_particles", '""')
    assert _job_dir.try_get_particle_number(job_dir) == 3


def test_particle_number_of_other_jobs(tmp_path: Path):
    job_dir = _copy_job(tmp_path, JOBS_DIR_SPA / "MotionCorr" / "job001", "MotionCorr/job002")
    assert _job_dir.try_get_particle_number(job_dir) == -1
