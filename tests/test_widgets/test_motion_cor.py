from typing import Callable
from qtpy.QtWidgets import QApplication
from pathlib import Path
import mrcfile
import numpy as np
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._frames import QMotionCorrViewer

def test_motioncor_widget(
    qtbot,
    make_job_directory: Callable[[str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "MotionCorr" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text)

    widget = QMotionCorrViewer(job_dir)
    qtbot.addWidget(widget)
    widget.initialize(job_dir)
    assert widget._mic_list.rowCount() == 0

    rng = np.random.default_rng(29958293)
    movies_path = job_dir.path / "Movies"
    movies_path.mkdir()
    basename = "Frame_00"
    shape = (10, 10)
    with mrcfile.new(movies_path.joinpath(f"{basename}.mrc")) as mrc:
        arr = rng.standard_normal(shape, dtype=np.float32).astype(np.float16)
        mrc.set_data(arr)
    widget.on_job_updated(job_dir, movies_path.joinpath(f"{basename}.mrc"))
    movies_path.joinpath(f"{basename}.log").write_text("log ...")
    widget.on_job_updated(job_dir, movies_path.joinpath(f"{basename}.log"))
    movies_path.joinpath(f"{basename}.star").write_text("star ...")
    widget.on_job_updated(job_dir, movies_path.joinpath(f"{basename}.star"))
    with mrcfile.new(movies_path.joinpath(f"{basename}_PS.mrc")) as mrc:
        arr = rng.standard_normal(shape, dtype=np.float32).astype(np.float16)
        mrc.set_data(arr)
    widget.on_job_updated(job_dir, movies_path.joinpath(f"{basename}_PS.mrc"))
    assert widget._mic_list.rowCount() == 1

    basename = "Frame_01"
    with mrcfile.new(movies_path.joinpath(f"{basename}.mrc")) as mrc:
        arr = rng.standard_normal(shape, dtype=np.float32).astype(np.float16)
        mrc.set_data(arr)
    widget.on_job_updated(job_dir, movies_path.joinpath(f"{basename}.mrc"))
    movies_path.joinpath(f"{basename}.log").write_text("log ...")
    widget.on_job_updated(job_dir, movies_path.joinpath(f"{basename}.log"))
    movies_path.joinpath(f"{basename}.star").write_text("star ...")
    widget.on_job_updated(job_dir, movies_path.joinpath(f"{basename}.star"))
    with mrcfile.new(movies_path.joinpath(f"{basename}_PS.mrc")) as mrc:
        arr = rng.standard_normal(shape, dtype=np.float32).astype(np.float16)
        mrc.set_data(arr)
    widget.on_job_updated(job_dir, movies_path.joinpath(f"{basename}_PS.mrc"))
    assert widget._mic_list.rowCount() == 2
    for _ in range(3):
        QApplication.processEvents()
