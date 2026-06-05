from typing import Callable
from qtpy.QtWidgets import QApplication
from pathlib import Path
import pytest
from himena import MainWindow, WidgetDataModel
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._class3d import QClass3DViewer
from himena_relion.schemas import ParticleMetaModel
from himena_relion.testing import JobWidgetTester

_BILD_TEXT = """
.color 0.166667 0 0.833333
.cylinder 192.261 192.261 132.16 215.955 215.955 137.824 7.41416
.color 0.166667 0 0.833333
.cylinder 172.616 202.082 151.04 190.416 228.723 162.368 7.41416
.color 0.166667 0 0.833333
.cylinder 202.082 172.616 151.04 228.723 190.416 162.368 7.41416
"""

def test_class3d_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
    himena_ui: MainWindow,
):
    star_text = Path(jobs_dir_spa / "Class3D" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Class3D")

    tester = JobWidgetTester(QClass3DViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)
    assert not tester.widget._viewer.has_image
    tester.widget.show()

    tester.write_text(
        "run_it000_data.star",
        ParticleMetaModel.example(size=4).to_string()
    )
    for class_id in [1, 2, 3]:
        tester.write_random_mrc(f"run_it000_class00{class_id}.mrc", (6, 6, 6))
        tester.write_text(f"run_it000_class00{class_id}_angdist.bild", _BILD_TEXT)

        tester.widget._arrow_visible.setChecked(True)
        tester.widget._arrow_visible.setChecked(False)
        QApplication.processEvents()

    tester.write_text("run_it000_model.star", _MODEL_STAR_TEXT)
    assert tester.widget._viewer.has_image
    assert tester.widget._iter_choice.maximum() == 0
    assert tester.widget._list_widget.rowCount() == 3

    ### Prepare iteration 1 ###

    tester.write_text(
        "run_it001_data.star",
        ParticleMetaModel.example(size=4).to_string()
    )
    for class_id in [1, 2, 3]:
        tester.write_random_mrc(f"run_it001_class00{class_id}.mrc", (6, 6, 6))
        tester.write_text(f"run_it001_class00{class_id}_angdist.bild", _BILD_TEXT)

        tester.widget._arrow_visible.setChecked(True)
        tester.widget._arrow_visible.setChecked(False)
        QApplication.processEvents()

    tester.write_text("run_it001_model.star", _MODEL_STAR_TEXT)

    assert tester.widget._viewer.has_image
    assert tester.widget._iter_choice.maximum() == 1
    assert tester.widget._list_widget.rowCount() == 3
    QApplication.processEvents()

    assert tester.widget._viewer.has_image
    assert tester.widget._iter_choice.maximum() == 1
    assert tester.widget._iter_choice.value() == 1
    tester.widget._iter_choice.setValue(0)
    QApplication.processEvents()
    assert tester.widget._list_widget.rowCount() == 3
    tester.widget._iter_choice.setValue(1)
    QApplication.processEvents()
    assert tester.widget._list_widget.rowCount() == 3

    tester.widget._list_widget.set_current_row(1)
    QApplication.processEvents()
    assert tester.widget._list_widget.rowCount() == 3

    with pytest.raises(FileNotFoundError):
        tester.widget._continue_from_here_clicked()

    tester.write_text("run_it001_optimiser.star", _OPTIMISER_STAR_TEXT)
    tester.widget._continue_from_here_clicked()

    himena_ui.exec_action(
        "himena-relion:show-summary-panel",
        model_context=WidgetDataModel(
            value=job_dir,
            type="relion_job.relion.class3d",
        )
    )

    himena_ui.exec_action(
        "himena-relion:inspect-classes",
        model_context=WidgetDataModel(
            value=job_dir,
            type="relion_job.relion.class3d",
        )
    )

_MODEL_STAR_TEXT = """
data_model_general
_rlnCurrentResolution 10.0
_rlnPixelSize 2.7
_rlnNrClasses 3
_rlnLogLikelihood 2.e+03

data_model_classes

loop_
_rlnReferenceImage #1
_rlnClassDistribution #2
_rlnEstimatedResolution #3
_rlnAccuracyRotations #4
_rlnAccuracyTranslationsAngst #5
Class3D/job025/run_it001_class001.mrc  0.20 5.0 0.50 1.0
Class3D/job025/run_it001_class002.mrc  0.50 6.0 0.30 1.1
Class3D/job025/run_it001_class003.mrc  0.30 7.0 0.20 0.8

data_model_groups

loop_
_rlnGroupNumber #1
_rlnGroupName #2
_rlnGroupNrParticles #3
1       Group1  100
1       Group1  200
1       Group1  300


"""


_OPTIMISER_STAR_TEXT = """
data_optimiser_general
_rlnCurrentIteration 1
_rlnOverallAccuracyRotations 0.5
_rlnOverallAccuracyTranslationsAngst 1.1
_rlnChangesOptimalOrientations 0.2
_rlnChangesOptimalOffsets 0.3
_rlnChangesOptimalClasses 0.7
"""
