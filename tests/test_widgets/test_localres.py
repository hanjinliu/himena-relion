from typing import Callable
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

    prev_job_dir = make_job_directory(
        Path(jobs_dir_spa / "Refine3D" / "job001" / "job.star").read_text(),
        "Refine3D/job100"
    )
    mrc0 = np.arange(32 * 32 * 32, dtype=np.float32).reshape((32, 32, 32))
    refine3d = JobWidgetTester.no_widget(prev_job_dir)
    refine3d.write_mrc("run_half1_class001_unfil.mrc", mrc0)
    refine3d.write_mrc("run_half2_class001_unfil.mrc", mrc0)
    xx, yy, zz = np.indices((32, 32, 32))
    sphere = (xx - 16) ** 2 + (yy - 16) ** 2 + (zz - 16) ** 2 < 14**2
    refine3d.write_mrc("mask.mrc", sphere.astype(np.float32))

    job_dir = make_job_directory(star_text, "LocalRes")
    tester = JobWidgetTester(QLocalResViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    tester.write_random_mrc("relion_locres.mrc", shape=(32, 32, 32))
    QApplication.processEvents()
    QApplication.processEvents()
    assert tester.widget._viewer._surface._data is not None
