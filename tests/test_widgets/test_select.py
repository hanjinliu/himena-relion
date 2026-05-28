from typing import Callable
from pathlib import Path
from starfile_rs import as_star
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._select import QRemoveDuplicatesViewer, QDiscardParticlesViewer, QSplitParticlesViewer
from himena_relion.relion5.widgets._join import QJoinParticleViewer
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


def test_discard_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "Select" / "job005" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Select")
    tester = JobWidgetTester(QDiscardParticlesViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)
    path_all = job_dir.relion_project_dir / job_dir.get_job_param("fn_data")
    job_dir.relion_project_dir.joinpath(path_all.parent).mkdir(parents=True, exist_ok=True)

    all_str = as_star(
        {
            "particles": {
                "rlnImageName": [f"000{i}@img.mrcs" for i in range(1, 6)]
            }
        }
    ).to_string()
    particles_star_str = as_star(
        {
            "particles": {
                "rlnImageName": [f"000{i}@img.mrcs" for i in [2, 4]]
            }
        }
    ).to_string()
    tester.write_text("particles.star", particles_star_str)
    job_dir.relion_project_dir.joinpath(path_all).write_text(all_str)
    tester.write_random_mrc("img.mrcs", (5, 10, 10))
    tester.write_exit_with_success()

    # subtomo
    all_str = as_star(
        {
            "particles": {
                "rlnTomoName": ["TS_01" for i in range(1, 6)],
                "rlnImageName": [f"img{i}_stack2d.mrc" for i in range(1, 6)]
            }
        }
    ).to_string()
    particles_star_str = as_star(
        {
            "particles": {
                "rlnTomoName": ["TS_01" for i in range(2)],
                "rlnImageName": [f"img{i}_stack2d.mrc" for i in [2, 4]]
            }
        }
    ).to_string()
    tester.write_text("particles.star", particles_star_str)
    job_dir.relion_project_dir.joinpath(path_all).write_text(all_str)
    for i in range(1, 6):
        tester.write_random_mrc(f"img{i}_stack2d.mrc", (5, 10, 10))
    tester.write_exit_with_success()

    # subtomo 3D
    all_str = as_star(
        {
            "particles": {
                "rlnTomoName": ["TS_01" for i in range(1, 6)],
                "rlnImageName": [f"img{i}_data.mrc" for i in range(1, 6)]
            }
        }
    ).to_string()
    particles_star_str = as_star(
        {
            "particles": {
                "rlnTomoName": ["TS_01" for i in range(2)],
                "rlnImageName": [f"img{i}_data.mrc" for i in [2, 4]]
            }
        }
    ).to_string()
    tester.write_text("particles.star", particles_star_str)
    job_dir.relion_project_dir.joinpath(path_all).write_text(all_str)
    for i in range(1, 6):
        tester.write_random_mrc(f"img{i}_data.mrc", (10, 10, 10))
    tester.write_exit_with_success()

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

def test_join_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    himena_ui,
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "JoinStar" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "JoinStar")

    tester = JobWidgetTester(QJoinParticleViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    tester.write_text("join_particles.star", ParticleMetaModel.example(40).to_string())
    tester.write_exit_with_success()
    # The combobox should have the block name as an item
    assert tester.widget._combobox.count() == 1
    assert tester.widget._combobox.itemText(0) == "particles"
