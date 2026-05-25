from typing import Callable
from pathlib import Path
from starfile_rs import as_star
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._subtract import QSubtractViewer
from himena_relion.testing import JobWidgetTester

def test_subtract_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "Subtract" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Subtract")

    tester = JobWidgetTester(QSubtractViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    path_orig = job_dir.path / "img_orig.mrcs"
    path_sub = job_dir.path / "img_sub.mrcs"
    tester.write_random_mrc(path_orig, (50, 12, 12))
    tester.write_random_mrc(path_sub, (50, 12, 12))

    star = as_star(
        {
            "particles": {
                "lnImageName": [
                    f"{ith + 1:08d}@Subtract/job025/img_sub.mrcs" for ith in range(50)
                ],
                "lnImageOriginalName": [
                    f"{ith + 1:08d}@Subtract/job025/img_orig.mrcs" for ith in range(50)
                ],
            }
        }
    )

    tester.write_text("particle_subtracted.star", star.to_string())
    tester.write_exit_with_success()
