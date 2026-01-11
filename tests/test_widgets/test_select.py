from typing import Callable
from pathlib import Path
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._select import QSplitParticlesViewer
from himena_relion.testing import JobWidgetTester
from himena_relion.schemas import ParticleMetaModel, ParticlesModel

def test_split_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "Select" / "job004" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Select")

    tester = JobWidgetTester(QSplitParticlesViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    tester.write_text("particles_split1.star", ParticleMetaModel.example(50).to_string())
    tester.write_text("particles_split2.star", ParticlesModel.example(30).to_string())
