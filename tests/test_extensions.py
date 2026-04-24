from typing import Callable
from pathlib import Path

import mrcfile
import numpy as np
from himena_relion._job_dir import JobDirectory
from himena_relion.testing import ExternalJobTester
from himena_relion.schemas import TSGroupModel, TSModel

def test_shift_map(qtbot, tmpdir):
    from himena_relion.relion5.extensions.transform import ShiftMapJob

    tmpdir = Path(tmpdir)
    ext_dir = tmpdir / "External/job010"
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_path = ext_dir / "in_3dref.mrc"
    mask_path = ext_dir / "in_mask.mrc"
    with mrcfile.new(img_path) as mrc:
        mrc.set_data(np.random.normal(size=(8, 8, 8)).astype(np.float32))
    with mrcfile.new(mask_path) as mrc:
        mrc.set_data(np.random.normal(size=(8, 8, 8)).astype(np.float32))
        mrc.voxel_size.nx = 0.78
        mrc.voxel_size.ny = 0.78
        mrc.voxel_size.nz = 0.78

    tester = ExternalJobTester(ShiftMapJob)
    widget = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)
    tester.prep_job_star(ext_dir, in_3dref=str(img_path), center_by="pixel", new_center=(1, 0, -1.2))
    tester.prep_job_star(ext_dir, in_3dref=str(img_path), center_by="angstrom", new_center=(1, 0, -1.2))
    tester.prep_job_star(ext_dir, in_3dref=str(img_path), center_by="map-com")
    tester.prep_job_star(ext_dir, in_3dref=str(img_path), in_mask=str(mask_path), center_by="map-com")

def test_exclude_tilts_job(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    from himena_relion.relion5_tomo.extensions.exclude_tilts import AutoExcludeTiltImages

    star_text = Path(jobs_dir_tomo).joinpath("CtfFind/job001/job.star").read_text()
    ctffind_dir = make_job_directory(star_text, "CtfFind")
    ctffind_dir.path.joinpath("frames").mkdir()
    ctffind_dir.path.joinpath("tilt_series").mkdir()
    ctffind_dir_rel = ctffind_dir.make_relative_path(ctffind_dir.path)

    rng = np.random.default_rng(291)
    ts_group = TSGroupModel(
        tomo_name=[f"TS_0{i}" for i in range(3)],
        tomo_tilt_series_star_file=[str(ctffind_dir_rel / f"tilt_series/TS_0{i}.star") for i in range(3)],
        voltage=[200, 200, 200],
        cs=[2.7, 2.7, 2.7],
        amplitude_contrast=[0.1, 0.1, 0.1],
        original_pixel_size=[1.0, 1.0, 1.0],
        tomo_hand=[1, 1, 1],
    )

    for i in range(3):
        gs = TSModel(
            frame_count=[4, 4, 4, 4, 4],
            nominal_stage_tilt_angle=[-40, -20, 0, 20, 60],
            nominal_tilt_axis_angle=[85, 85, 85, 85, 85],
            pre_exposure=[0, 0, 0, 0, 0],
            nominal_defocus=[-2, -2, -2, -2, -2],
            micrograph_name=[f"TS_0{i}_{j}.mrc" for j in range(5)],
        )
        for j in range(5):
            star_stem = f"TS_0{i}_{j}"
            path_mrc = ctffind_dir.path.joinpath(f"frames/{star_stem}.mrc")
            with mrcfile.new(path_mrc) as mrc:
                if j == 0:
                    img = -np.ones((8, 8), dtype=np.float32)
                else:
                    img = rng.normal(size=(8, 8)).astype(np.float32)
                mrc.set_data(img)

        ctffind_dir.path.joinpath(f"tilt_series/TS_0{i}.star").write_text(gs.to_string())

    ctffind_dir.path.joinpath("tilt_series_ctf.star").write_text(ts_group.to_string())

    ext_dir = ctffind_dir.relion_project_dir.joinpath("External/job039")
    ext_dir.mkdir(parents=True, exist_ok=True)

    tester = ExternalJobTester(AutoExcludeTiltImages)
    tester.prep_job_star(ext_dir, in_mics=ctffind_dir_rel/"tilt_series_ctf.star")
    widget = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)

    tester.test_run(ext_dir, widget=widget)
