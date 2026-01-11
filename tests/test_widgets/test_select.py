from typing import Callable
from pathlib import Path
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._select import QRemoveDuplicatesViewer, QSplitParticlesViewer
from himena_relion.testing import JobWidgetTester
from himena_relion.schemas import ParticleMetaModel, ParticlesModel

def test_remove_duplicates_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "Select" / "job002" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Select")

    tester = JobWidgetTester(QRemoveDuplicatesViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    tester.write_text("particles.star", ParticleMetaModel.example(60).to_string())
    tester.write_text("particles_removed.star", ParticlesModel.example(20).to_string())
    tester.write_exit_with_success()
    plain_text = tester.widget._text_edit.toPlainText()
    assert "60" in plain_text
    assert "20" in plain_text
    assert "25.00%" in plain_text
    assert "75.00%" in plain_text
    assert "100%" in plain_text

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
    tester.write_exit_with_success()
    plain_text = tester.widget._text_edit.toPlainText()
    assert "particles_split1.star" in plain_text
    assert "50 particles" in plain_text
    assert "particles_split2.star" in plain_text
    assert "30 particles" in plain_text
