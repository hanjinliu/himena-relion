import time
from typing import Callable
from pathlib import Path

import threading
import mrcfile
import numpy as np
import polars as pl
from starfile_rs import as_star, read_star
from himena_relion._job_dir import JobDirectory
from himena_relion.testing import ExternalJobTester
from himena_relion.schemas import (
    TSGroupModel,
    TSModel,
    RelionPipelineModel,
    TomogramsGroupModel,
    CoordsModel,
    MicrographsStarModel,
    ParticleMetaModel,
    ParticlesModel,
)

def test_shift_map(qtbot, tmpdir):
    from himena_relion.relion5.extensions import ShiftMapJob

    tmpdir = Path(tmpdir)
    ext_dir = tmpdir / "External/job010"
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_path = ext_dir / "in_3dref.mrc"
    mask_path = ext_dir / "in_mask.mrc"
    with mrcfile.new(img_path) as mrc:
        mrc.set_data(np.random.normal(size=(8, 8, 8)).astype(np.float32))
    with mrcfile.new(mask_path) as mrc:
        mrc.set_data(np.random.normal(size=(8, 8, 8)).astype(np.float32))
        mrc.voxel_size = (0.78, 0.78, 0.78)

    tester = ExternalJobTester(ShiftMapJob)
    widget = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)
    tester.prep_job_star(ext_dir, in_3dref=str(img_path), center_by="pixel", new_center=(1, 0, -1.2))
    tester.prep_job_star(ext_dir, in_3dref=str(img_path), center_by="angstrom", new_center=(1, 0, -1.2))
    tester.prep_job_star(ext_dir, in_3dref=str(img_path), center_by="map-com")
    tester.prep_job_star(ext_dir, in_3dref=str(img_path), in_mask=str(mask_path), center_by="map-com")

def test_inspect_particles_spa(qtbot, tmpdir):
    from himena_relion.relion5.extensions.inspect_particles import InspectParticlesSPA, InspectParticlesSPAWidget

    tmpdir = Path(tmpdir)
    mic_dir = tmpdir / "micrographs"
    mic_dir.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        with mrcfile.new(mic_dir / f"mic{i}.mrc") as mrc:
            mrc.set_data(np.random.normal(size=(8, 8)).astype(np.float32))
            mrc.voxel_size = (0.78, 0.78, 0.78)

    ext_dir = tmpdir / "External/job010"
    ext_dir.mkdir(parents=True, exist_ok=True)
    mic_path = ext_dir / "micrographs.star"
    parts_path = ext_dir / "particles.star"

    mic_path.write_text(
        MicrographsStarModel(
            optics=MicrographsStarModel.Optics(
                optics_group_name=["group1"],
                optics_group=[1],
                mic_orig_pixel_size=[0.78],
                voltage=[300],
                cs=[2.7],
            ),
            micrographs=MicrographsStarModel.Micrographs(
                mic_name=[f"micrographs/mic{i}.mrc" for i in range(3)],
                optics_group=[1, 1, 1],
            )
        ).to_string()
    )
    parts_path.write_text(
        CoordsModel(
            x=[4, 5, 4, 5, 6, 7, 8, 3, 4],
            y=[4, 4, 5, 5, 6, 7, 8, 3, 4],
            orig_x=[0.1] * 9,
            orig_y=[0.1] * 9,
            mic_name=[f"mic{i}.mrc" for i in [0, 0, 0, 1, 1, 1, 2, 2, 2]],
        ).to_string()
    )

    tester = ExternalJobTester(InspectParticlesSPA)
    widget = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)
    tester.prep_job_star(ext_dir, in_mics=str(mic_path), in_parts=str(parts_path))
    tester.test_run(ext_dir, widget=widget)
    assert isinstance(widget, InspectParticlesSPAWidget)
    widget._show_points_switch.value = False
    widget._show_points_switch.value = True

def _prep_ctffind_job(ctffind_dir: JobDirectory):
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
            micrograph_name=[
                str(ctffind_dir_rel / f"frames/TS_0{i}_{j}.mrc") for j in range(5)
            ],
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
                mrc.voxel_size = (0.78, 0.78, 0.78)

        ctffind_dir.path.joinpath(f"tilt_series/TS_0{i}.star").write_text(gs.to_string())

    ctffind_dir.path.joinpath("tilt_series_ctf.star").write_text(ts_group.to_string())


def test_exclude_tilts_job(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    from himena_relion.relion5_tomo.extensions import AutoExcludeTiltImages

    star_text = Path(jobs_dir_tomo).joinpath("CtfFind/job001/job.star").read_text()
    ctffind_dir = make_job_directory(star_text, "CtfFind")
    _prep_ctffind_job(ctffind_dir)
    ctffind_dir_rel = ctffind_dir.make_relative_path(ctffind_dir.path)

    ext_dir = ctffind_dir.relion_project_dir.joinpath("External/job039")
    ext_dir.mkdir(parents=True, exist_ok=True)

    tester = ExternalJobTester(AutoExcludeTiltImages)
    tester.prep_job_star(ext_dir, in_mics=ctffind_dir_rel/"tilt_series_ctf.star")
    widget = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)

    tester.test_run(ext_dir, widget=widget)

def _findbeads3d_wrapped(
    exe: str,
    tomo_path: str | Path,
    out_path: str | Path,
    size_pix: float,
    angle_range: tuple[float, float] = (-60.0, 60.0),
):
    import imodmodel
    import pandas as pd

    df = pd.DataFrame({"x": [0, 10], "y": [0, 40], "z": [0, 10]})
    imodmodel.write(df, out_path)

def test_erase_gold(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
    monkeypatch,
):
    from himena_relion.relion5_tomo.extensions.erase_gold import (
        FindBeads3D, EraseGold, _impl
    )

    monkeypatch.setattr(_impl, "findbeads3d_wrapped", _findbeads3d_wrapped)

    star_text = Path(jobs_dir_tomo).joinpath("CtfFind/job001/job.star").read_text()
    ctffind_dir = make_job_directory(star_text, "CtfFind")
    _prep_ctffind_job(ctffind_dir)
    ctffind_dir_rel = ctffind_dir.make_relative_path(ctffind_dir.path)
    with mrcfile.new(ctffind_dir.path.joinpath("tomo.mrc")) as mrc:
        mrc.set_data(np.ones((8, 8, 8), dtype=np.float32))
    df = read_star(
        ctffind_dir.path.joinpath("tilt_series_ctf.star")
    ).first().to_polars()
    df = df.with_columns(
        pl.lit(str(ctffind_dir_rel/"tomo.mrc")).alias("rlnTomoReconstructedTomogram"),
        pl.lit(str(ctffind_dir_rel/"tomo.edf")).alias("rlnEtomoDirectiveFile"),
    )
    np.savetxt(
        ctffind_dir.path / "tomo.xf",
        np.array([[0.01, 0.99, -0.99, 0.01, -1, 2]] * 5),
        delimiter=" ",
    )

    as_star({"global": df}).write(ctffind_dir.path.joinpath("tilt_series_ctf.star"))

    findbeads_dir = ctffind_dir.relion_project_dir.joinpath("External/job039")
    findbeads_dir.mkdir(parents=True, exist_ok=True)
    tester = ExternalJobTester(FindBeads3D)
    tester.prep_job_star(
        findbeads_dir,
        findbeads3d_exe="***",
        in_mics=ctffind_dir_rel/"tilt_series_ctf.star"
    )
    findbeads_dir.joinpath("job_pipeline.star").write_text(
        RelionPipelineModel(
            general=RelionPipelineModel.General(count=5),
            processes=RelionPipelineModel.Processes(
                process_name=["External/job039/"],
                alias=["alias"],
                type_label=["type"],
                status_label=["Succeeded"],
            ),
            nodes=RelionPipelineModel.Nodes(
                name=[str(ctffind_dir_rel/"tilt_series_ctf.star")],
                type_label=["TomogramGroupMetadata.star"],
                type_label_depth=[1],
            ),
            input_edges=RelionPipelineModel.InputEdges(
                from_node=[str(ctffind_dir_rel/"tilt_series_ctf.star")],
                process=["External/job039/"],
            )
        ).to_string()
    )
    widget = tester.provide_widget(findbeads_dir)
    qtbot.addWidget(widget)
    tester.test_run(findbeads_dir, widget=widget)

    erasegold_dir = ctffind_dir.relion_project_dir.joinpath("External/job040")
    erasegold_dir.mkdir(parents=True, exist_ok=True)
    tester = ExternalJobTester(EraseGold)
    tester.prep_job_star(erasegold_dir, in_mics="External/job039/tomograms.star")
    widget = tester.provide_widget(erasegold_dir)
    qtbot.addWidget(widget)
    tester.test_run(erasegold_dir, widget=widget)

def test_take_zerotilts(
    qtbot,
    tmpdir,
    jobs_dir_tomo,
):
    from himena_relion.relion5_tomo.extensions import TakeZeroTiltMicrographs

    rln_dir = Path(tmpdir)
    frames_dir = rln_dir.joinpath("frames")
    frames_dir.mkdir(parents=True, exist_ok=True)
    for i in range(4):
        for j in range(5):
            with mrcfile.new(frames_dir.joinpath(f"TS_0{i}_{j}.mrc")) as mrc:
                mrc.set_data(np.random.normal(size=(8, 8)).astype(np.float32))
                mrc.voxel_size = (0.78, 0.78, 0.78)

    some_dir = rln_dir.joinpath("some_dir")
    tilt_series_dir = some_dir.joinpath("tilt_series")
    some_dir.mkdir(parents=True, exist_ok=True)
    tilt_series_dir.mkdir()

    # frames/
    #   TS_00_00.mrc
    #   TS_00_01.mrc
    #   ...
    # some_dir/
    #   tilt_series/
    #     TS_00.star
    #     TS_01.star
    #     ...
    #   tomograms.star
    #   run_data.star

    for i in range(4):
        ts_star = TSModel(
            movie_name=[f"TS_0{i}_{j}.mrc" for j in range(5)],
            frame_count=[4] * 5,
            nominal_stage_tilt_angle=[-40, -20, 0, 20, 60],
            nominal_tilt_axis_angle=[85] * 5,
            pre_exposure=[0] * 5,
            nominal_defocus=[-2] * 5,
            micrograph_name=[f"frames/TS_0{i}_{j}.mrc" for j in range(5)],
            tomo_xtilt=[1, 1, 2, 1, 2],
            tomo_ytilt=[1, 1, 2, 1, 2],
            tomo_zrot=[0, 0, 0, 0, 0],
            tomo_xshift_angst=[0.2, 0.2, 0.3, 0.2, 0.3],
            tomo_yshift_angst=[0.2, 0.2, 0.3, 0.2, 0.3],
        )
        tilt_series_dir.joinpath(f"TS_0{i}.star").write_text(ts_star.to_string())

    tomogram_star = TomogramsGroupModel(
        tomo_name=[f"TS_0{i}" for i in range(4)],
        voltage=[300] * 4,
        cs=[2.7] * 4,
        amplitude_contrast=[0.1] * 4,
        original_pixel_size=[0.78] * 4,
        tomo_hand=[1] * 4,
        optics_group_name=["group1", "group1", "group2", "group2"],
        tomo_tilt_series_pixel_size=[0.78, 0.78, 0.78, 0.78],
        tomo_tilt_series_star_file=[f"some_dir/tilt_series/TS_0{i}.star" for i in range(4)],
        tomogram_binning=[1.0] * 4,
        size_x=[4000] * 4,
        size_y=[3000] * 4,
        size_z=[1000] * 4,
    )
    some_dir.joinpath("tomograms.star").write_text(tomogram_star.to_string())

    run_data = ParticleMetaModel(
        particles=ParticlesModel(
            tomo_name=[f"TS_0{i}" for i in range(4) for _ in range(10)],
            centered_x=[0.0] * 40,
            centered_y=[0.0] * 40,
            centered_z=[0.0] * 40,
            orig_x=[0.0] * 40,
            orig_y=[0.0] * 40,
            orig_z=[0.0] * 40,
            angle_rot=[0.0] * 40,
            angle_tilt=[0.0] * 40,
        )
    )
    some_dir.joinpath("particles.star").write_text(run_data.to_string())

    ext_dir = rln_dir.joinpath("External/job001")
    ext_dir.mkdir(parents=True, exist_ok=True)
    tester = ExternalJobTester(TakeZeroTiltMicrographs)
    tester.prep_job_star(ext_dir, in_mics="some_dir/tomograms.star", in_parts="some_dir/particles.star")
    widget = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)
    tester.test_run(ext_dir, widget=widget)

def test_manually_create_mask(
    qtbot,
    tmpdir,
    jobs_dir_spa,
):
    from himena_relion.relion5.extensions.volume_tools import ManualMaskCreation

    tmpdir = Path(tmpdir)
    template_path = tmpdir / "in_3dref.mrc"
    with mrcfile.new(template_path) as mrc:
        mrc.set_data(np.random.normal(size=(8, 8, 8)).astype(np.float32))
        mrc.voxel_size = (0.78, 0.78, 0.78)
    ext_dir = tmpdir / "External/job010"
    ext_dir.mkdir(parents=True, exist_ok=True)

    tester = ExternalJobTester(ManualMaskCreation)
    ManualMaskCreation._max_wait_time_sec = 5
    tester.prep_job_star(ext_dir, in_3dref=str(template_path))
    widget = tester.provide_widget(ext_dir)
    qtbot.addWidget(widget)

    mask_path = ext_dir / "mask_base.mrc"
    def create_mask():
        time.sleep(0.5)
        with mrcfile.new(mask_path) as mrc:
            mrc.set_data(np.random.normal(size=(8, 8, 8)).astype(np.float32))
            mrc.voxel_size = (0.78, 0.78, 0.78)

    thread = threading.Thread(target=create_mask, daemon=True)
    thread.start()

    tester.test_run(ext_dir, widget=widget)
