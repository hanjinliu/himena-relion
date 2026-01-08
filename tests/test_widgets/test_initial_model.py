from typing import Callable
from qtpy.QtWidgets import QApplication
from pathlib import Path
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._initial_model import QInitialModelViewer
from himena_relion.schemas import ParticleMetaModel, ModelStarModel
from himena_relion.testing import JobWidgetTester

_BILD_TEXT = """
.color 0.166667 0 0.833333
.cylinder 192.261 192.261 132.16 215.955 215.955 137.824 7.41416
.color 0.166667 0 0.833333
.cylinder 172.616 202.082 151.04 190.416 228.723 162.368 7.41416
.color 0.166667 0 0.833333
.cylinder 202.082 172.616 151.04 228.723 190.416 162.368 7.41416
"""

def test_initial_model_widget(
    qtbot,
    make_job_directory: Callable[[str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "InitialModel" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text)

    tester = JobWidgetTester(QInitialModelViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)
    assert not tester.widget._viewer.has_image

    tester.write_text(
        "run_it000_data.star",
        ParticleMetaModel.example(size=4).to_string()
    )
    tester.write_text(
        "run_it000_model.star",
        ModelStarModel.example(size=3).to_string()
    )

    for class_id in [1, 2, 3]:
        tester.write_random_mrc(f"run_it000_class00{class_id}.mrc", (6, 6, 6))
        tester.write_text(f"run_it000_class00{class_id}_angdist.bild", _BILD_TEXT)

        assert tester.widget._viewer.has_image
        assert tester.widget._iter_choice.maximum() == 0
    assert tester.widget._class_choice.minimum() == 1
    assert tester.widget._class_choice.maximum() == 3

    ### Prepare iteration 10 ###

    tester.write_text(
        "run_it010_data.star",
        ParticleMetaModel.example(size=4).to_string()
    )
    tester.write_text(
        "run_it010_model.star",
        ModelStarModel.example(size=3).to_string()
    )

    for class_id in [1, 2, 3]:
        tester.write_random_mrc(f"run_it010_class00{class_id}.mrc", (6, 6, 6))
        assert tester.widget._viewer.has_image
        tester.write_text(f"run_it010_class00{class_id}_angdist.bild", _BILD_TEXT)

    assert tester.widget._viewer.has_image
    assert tester.widget._iter_choice.maximum() == 10
    assert tester.widget._iter_choice.value() == 10
    assert tester.widget._class_choice.minimum() == 1
    assert tester.widget._class_choice.maximum() == 3

    tester.widget._iter_choice.setValue(0)
    QApplication.processEvents()
    tester.widget._iter_choice.setValue(10)
    QApplication.processEvents()

    for _ in range(10):
        QApplication.processEvents()
