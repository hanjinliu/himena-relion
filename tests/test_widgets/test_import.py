from typing import Callable
import tifffile
from pathlib import Path
import numpy as np
from himena_relion._job_dir import JobDirectory
from himena_relion.testing import JobWidgetTester
from himena_relion.schemas import MoviesStarModel, TSGroupModel, TSModel

def test_import_spa_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    from himena_relion.relion5.widgets._frames import QImportMoviesViewer

    star_text = Path(jobs_dir_spa / "Import" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Import")

    tester = JobWidgetTester(QImportMoviesViewer(job_dir), job_dir)

    qtbot.addWidget(tester.widget)
    raw_frames_dir = job_dir.relion_project_dir / "frames"
    raw_frames_dir.mkdir()
    movies = []
    for i in range(3):
        tiff_path = raw_frames_dir / f"Frame_{i:02d}.tif"
        frame_img = _random_movie(tester)
        with tifffile.TiffWriter(tiff_path) as tif:
            tif.write(frame_img, compression="lzw")
        movies.append(tiff_path.relative_to(job_dir.relion_project_dir).as_posix())

    model = MoviesStarModel(
        optics=MoviesStarModel.Optics(
            optics_group_name=["optics1"],
            optics_group=[1],
            mtf_file_name=[""],
            mic_orig_pixel_size=[1.0],
            voltage=[300.0],
            cs=[2.7],
            amplitude_contrast=[0.1],
        ),
        movies=MoviesStarModel.Movies(movie_name=movies, optics_group=[1, 1, 1]),
    )
    tester.write_text("movies.star", model.to_string())
    assert tester.widget._mic_list.rowCount() == 3
    tester.widget._mic_list.setCurrentCell(1, 0)
    tester.widget._mic_list.setCurrentCell(2, 0)
    tester.widget._mic_list.setCurrentCell(0, 0)

def test_import_tomo_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    from himena_relion.relion5_tomo.widgets._import import QImportTiltSeriesViewer

    star_text = Path(jobs_dir_spa / "Import" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Import")

    tester = JobWidgetTester(QImportTiltSeriesViewer(job_dir), job_dir)

    qtbot.addWidget(tester.widget)
    assert tester.widget._ts_list.rowCount() == 0
    tester.mkdir("tilt_series")

    raw_frames_dir = job_dir.relion_project_dir / "frames"
    raw_frames_dir.mkdir()

    for i in range(3):  # i-th tilt series
        for i_tilt in range(5):
            tiff_path = raw_frames_dir / f"TS_{i+1:02d}_{i_tilt:03d}.tif"
            frame_img = _random_movie(tester)
            with tifffile.TiffWriter(tiff_path) as tif:
                tif.write(frame_img, compression="lzw")
        ts = TSModel(
            movie_name=[f"frames/TS_{i+1:02d}_{j:03d}" for j in range(5)],
            frame_count=[4] * 5,
            nominal_stage_tilt_angle=[-60 + j * 30 for j in range(5)],
            nominal_tilt_axis_angle=[0.0] * 5,
            pre_exposure=[0.0, 5.0, 10.0, 15.0, 20.0],
            nominal_defocus=[3.5] * 5,
            micrograph_name=[""] * 5,
            micrograph_movie_name=[""] * 5,
            ctf_image=[""] * 5,
        )
        tester.write_text(f"tilt_series/TS_{i+1:02d}.star", ts.to_string())

    model = TSGroupModel(
        tomo_name=[f"TS_{i+1:02d}" for i in range(3)],
        tomo_tilt_series_star_file=[f"tilt_series/TS_{i+1:02d}.star" for i in range(3)],
        voltage=[300.0] * 3,
        cs=[2.7] * 3,
        amplitude_contrast=[0.1] * 3,
        original_pixel_size=[0.84 for i in range(3)],
        tomo_hand=[-1] * 3,
        optics_group_name=["optics1"] * 3,
    )
    tester.write_text("tilt_series.star", model.to_string())

def _random_movie(tester: JobWidgetTester):
    return tester._rng.integers(-100, 100, (4, 6)).astype(np.int8)
