import shutil
from typing import Callable
import mrcfile
import numpy as np
from qtpy.QtWidgets import QApplication
from pathlib import Path
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._localres import QLocalResViewer
from himena_relion.testing import JobWidgetTester

def test_localres_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    # LocalRes widget requires previous job to work properly
    star_text = Path(jobs_dir_spa / "LocalRes" / "job001" / "job.star").read_text()
    lines = []
    for line in star_text.splitlines():
        if line.strip().startswith("fn_in"):
            line = "fn_in   Refine3D/job100/run_half1_class001_unfil.mrc"
        elif line.strip().startswith("fn_mask"):
            line = "fn_mask   Refine3D/job100/mask.mrc"
        lines.append(line)
    star_text = "\n".join(lines)

    job_dir = make_job_directory(star_text, "LocalRes")

    prev_job = job_dir.path.parent.parent.joinpath("Refine3D", "job100")
    prev_job.mkdir(parents=True)
    mrc0 = np.arange(32 * 32 * 32, dtype=np.float32).reshape((32, 32, 32))
    with mrcfile.new(prev_job / "run_half1_class001_unfil.mrc") as mrc:
        mrc.set_data(mrc0)
    with mrcfile.new(prev_job / "run_half2_class001_unfil.mrc") as mrc:
        mrc.set_data(mrc0)
    with mrcfile.new(prev_job / "mask.mrc") as mrc:
        xx, yy, zz = np.indices((32, 32, 32))
        sphere = (xx - 16) ** 2 + (yy - 16) ** 2 + (zz - 16) ** 2 < 14**2
        mrc.set_data(sphere.astype(np.float32))

    tester = JobWidgetTester(QLocalResViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    tester.write_random_mrc("relion_locres.mrc", shape=(32, 32, 32))
    QApplication.processEvents()
    QApplication.processEvents()
    assert tester.widget._viewer._surface._data is not None

    shutil.rmtree(prev_job)
