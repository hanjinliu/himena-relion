from typing import Callable
from qtpy.QtWidgets import QApplication
from pathlib import Path
import mrcfile
import numpy as np
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._refine import QRefine3DViewer
from himena_relion.schemas import ParticleMetaModel

_BILD_TEXT = """
.color 0.166667 0 0.833333
.cylinder 192.261 192.261 132.16 215.955 215.955 137.824 7.41416
.color 0.166667 0 0.833333
.cylinder 172.616 202.082 151.04 190.416 228.723 162.368 7.41416
.color 0.166667 0 0.833333
.cylinder 202.082 172.616 151.04 228.723 190.416 162.368 7.41416
"""

def test_refine3d_widget(
    qtbot,
    make_job_directory: Callable[[str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "Refine3D" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text)

    rng = np.random.default_rng(29958293)
    widget = QRefine3DViewer(job_dir)
    qtbot.addWidget(widget)
    widget.initialize(job_dir)
    assert not widget._viewer.has_image

    data_path = job_dir.path / "run_it000_data.star"
    ParticleMetaModel.example(size=4).write(data_path)
    widget.on_job_updated(job_dir, data_path)
    shape = (6, 6, 6)
    mrc_path = job_dir.path / "run_it000_half1_class001.mrc"
    with mrcfile.new(mrc_path) as mrc:
        arr = rng.standard_normal(shape, dtype=np.float32)
        mrc.set_data(arr)
    widget.on_job_updated(job_dir, mrc_path)

    bild_path = job_dir.path.joinpath("run_it000_half1_class001_angdist.bild")
    bild_path.write_text(_BILD_TEXT)
    widget._arrow_visible.setChecked(True)
    widget.on_job_updated(job_dir, bild_path)

    mrc_path = job_dir.path / "run_it000_half2_class001.mrc"
    with mrcfile.new(mrc_path) as mrc:
        arr = rng.standard_normal(shape, dtype=np.float32)
        mrc.set_data(arr)

    widget.on_job_updated(job_dir, mrc_path)
    assert widget._viewer.has_image
    assert widget._iter_choice.maximum() == 0

    ### Prepare iteration 1 ###

    data_path = job_dir.path / "run_it001_data.star"
    ParticleMetaModel.example(size=4).write(data_path)
    widget.on_job_updated(job_dir, data_path)
    shape = (6, 6, 6)
    mrc_path = job_dir.path / "run_it001_half1_class001.mrc"
    with mrcfile.new(mrc_path) as mrc:
        arr = rng.standard_normal(shape, dtype=np.float32)
        mrc.set_data(arr)
    widget.on_job_updated(job_dir, mrc_path)
    mrc_path = job_dir.path / "run_it001_half2_class001.mrc"
    with mrcfile.new(mrc_path) as mrc:
        arr = rng.standard_normal(shape, dtype=np.float32)
        mrc.set_data(arr)

    widget.on_job_updated(job_dir, mrc_path)
    assert widget._viewer.has_image

    bild_path = job_dir.path.joinpath("run_it001_half1_class001_angdist.bild")
    bild_path.write_text(_BILD_TEXT)
    widget._arrow_visible.setChecked(True)
    widget.on_job_updated(job_dir, bild_path)
    assert widget._viewer.has_image
    assert widget._iter_choice.maximum() == 1
    assert widget._iter_choice.value() == 1
    widget._iter_choice.setValue(0)
    QApplication.processEvents()
    widget._iter_choice.setValue(1)
    QApplication.processEvents()

    for _ in range(3):
        QApplication.processEvents()
