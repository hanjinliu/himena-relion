from typing import Callable
from pathlib import Path
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._pick import QManualPickViewer, QLoGPickViewer, QTopazTrainPickViewer
from himena_relion.schemas import CoordsModel, MicrographsStarModel
from himena_relion.testing import JobWidgetTester

def test_manual_pick_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    _prep_mcor_jobdir(jobs_dir_spa, make_job_directory)

    star_text = Path(jobs_dir_spa / "ManualPick" / "job001" / "job.star").read_text()
    star_lines = []
    for line in star_text.splitlines():
        if line.strip().startswith("fn_in"):
            star_lines.append("fn_in  MotionCorr/job001/corrected_micrographs.star")
        else:
            star_lines.append(line)
    star_text = "\n".join(star_lines)
    job_dir = make_job_directory(star_text, "ManualPick")
    tester = JobWidgetTester(QManualPickViewer(job_dir), job_dir)

    qtbot.addWidget(tester.widget)
    tester.mkdir("Movies")

    assert tester.widget._mic_list.rowCount() == 3
    assert tester.widget._mic_list.text(0, 1) == "0"
    assert tester.widget._mic_list.text(1, 1) == "0"
    assert tester.widget._mic_list.text(2, 1) == "0"

    m = CoordsModel(x=[12, 15, 14], y=[3, 21, 3])
    tester.write_text("Movies/Frame_01_manualpick.star", m.to_string())

    assert tester.widget._mic_list.rowCount() == 3
    assert tester.widget._mic_list.text(0, 1) == "3"
    assert tester.widget._mic_list.text(1, 1) == "0"
    assert tester.widget._mic_list.text(2, 1) == "0"

    tester.widget._mic_list.set_current_row(1)

    m = CoordsModel(x=[12, 15, 14, 30], y=[3, 21, 3, 18])
    tester.write_text("Movies/Frame_02_manualpick.star", m.to_string())

    assert tester.widget._mic_list.rowCount() == 3
    assert tester.widget._mic_list.text(0, 1) == "3"
    assert tester.widget._mic_list.text(1, 1) == "4"
    assert tester.widget._mic_list.text(2, 1) == "0"

    assert tester.widget._mic_list.selectionModel().currentIndex().row() == 1

    m = CoordsModel(x=[5], y=[12])
    tester.write_text("Movies/Frame_03_manualpick.star", m.to_string())

    assert tester.widget._mic_list.rowCount() == 3
    assert tester.widget._mic_list.text(0, 1) == "3"
    assert tester.widget._mic_list.text(1, 1) == "4"
    assert tester.widget._mic_list.text(2, 1) == "1"

    tester.widget._filter_widget.set_params(2, 0.04)

def test_log_pick_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    _prep_mcor_jobdir(jobs_dir_spa, make_job_directory)

    star_text = Path(jobs_dir_spa / "AutoPick" / "job001" / "job.star").read_text()
    star_lines = []
    for line in star_text.splitlines():
        if line.strip().startswith("fn_input_autopick"):
            star_lines.append("fn_input_autopick  MotionCorr/job001/corrected_micrographs.star")
        else:
            star_lines.append(line)
    star_text = "\n".join(star_lines)
    job_dir = make_job_directory(star_text, "AutoPick")
    tester = JobWidgetTester(QLoGPickViewer(job_dir), job_dir)

    qtbot.addWidget(tester.widget)
    tester.mkdir("Movies")

    assert tester.widget._mic_list.rowCount() == 3
    assert tester.widget._mic_list.text(0, 1) == "0"
    assert tester.widget._mic_list.text(1, 1) == "0"
    assert tester.widget._mic_list.text(2, 1) == "0"

    m = CoordsModel(x=[12, 15, 14], y=[3, 21, 3])
    tester.write_text("Movies/Frame_01_autopick.star", m.to_string())

    assert tester.widget._mic_list.rowCount() == 3
    assert tester.widget._mic_list.text(0, 1) == "3"
    assert tester.widget._mic_list.text(1, 1) == "0"
    assert tester.widget._mic_list.text(2, 1) == "0"

    tester.widget._mic_list.set_current_row(1)

    m = CoordsModel(x=[12, 15, 14, 30], y=[3, 21, 3, 18])
    tester.write_text("Movies/Frame_02_autopick.star", m.to_string())

    assert tester.widget._mic_list.rowCount() == 3
    assert tester.widget._mic_list.text(0, 1) == "3"
    assert tester.widget._mic_list.text(1, 1) == "4"
    assert tester.widget._mic_list.text(2, 1) == "0"

    assert tester.widget._mic_list.selectionModel().currentIndex().row() == 1

    m = CoordsModel(x=[5], y=[12])
    tester.write_text("Movies/Frame_03_autopick.star", m.to_string())

    assert tester.widget._mic_list.rowCount() == 3
    assert tester.widget._mic_list.text(0, 1) == "3"
    assert tester.widget._mic_list.text(1, 1) == "4"
    assert tester.widget._mic_list.text(2, 1) == "1"

# model_training.txt has columns:
# epoch, iter, split, loss, ge_penalty, precision, tpr, fpr, auprc
_TOPAZ_MODEL_TRAINING_TEXT = \
"""epoch\titer\tsplit\tloss\tge_penalty\tprecision\ttpr\tfpr\tauprc
1\t1\ttrain\t0.5\t0.01\t0.8\t0.7\t0.1\t-
1\t1\ttrain\t0.4\t0.01\t0.8\t0.75\t0.08\t-
1\t1\ttrain\t0.3\t0.01\t0.9\t0.8\t0.06\t-
1\t2\ttrain\t0.2\t0.01\t0.9\t0.85\t0.04\t-
1\t2\ttrain\t0.1\t0.01\t0.9\t0.9\t0.02\t-
1\t2\ttrain\t0.6\t0.01\t0.7\t0.65\t0.12\t-
1\t3\ttest\t0.5\t-\t0.8\t0.7\t0.1\t0.85
2\t1\ttrain\t0.5\t0.01\t0.8\t0.7\t0.1\t-
2\t1\ttrain\t0.4\t0.01\t0.8\t0.75\t0.08\t-
2\t1\ttrain\t0.3\t0.01\t0.9\t0.8\t0.06\t-
2\t2\ttrain\t0.2\t0.01\t0.9\t0.85\t0.04\t-
2\t2\ttrain\t0.1\t0.01\t0.9\t0.9\t0.02\t-
2\t2\ttrain\t0.6\t0.01\t0.7\t0.65\t0.12\t-
2\t3\ttest\t0.5\t-\t0.8\t0.7\t0.1\t0.85
"""

def test_topaz_train_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):

    star_text = Path(jobs_dir_spa / "AutoPick" / "job002" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "AutoPick")
    tester = JobWidgetTester(QTopazTrainPickViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    tester.write_text("model_training.txt", _TOPAZ_MODEL_TRAINING_TEXT)
    tester.write_text("mock.sav", "")


def _prep_mcor_jobdir(
    jobs_dir_spa: Path,
    make_job_directory: Callable[[str, str], JobDirectory]
) -> JobDirectory:
    star_text_mcor = Path(jobs_dir_spa / "MotionCorr" / "job001" / "job.star").read_text()
    job_dir_pre = make_job_directory(star_text_mcor, "MotionCorr/job001")

    mcor_obj = JobWidgetTester.no_widget(job_dir_pre)
    mcor_obj.mkdir("Movies")
    mcor_obj.write_random_mrc("Movies/Frame_01.mrc", (32, 32))
    mcor_obj.write_random_mrc("Movies/Frame_02.mrc", (32, 32))
    mcor_obj.write_random_mrc("Movies/Frame_03.mrc", (32, 32))
    m = MicrographsStarModel(
        optics=MicrographsStarModel.Optics(
            optics_group_name=["optics1"],
            optics_group=[1],
            mtf_file_name=[""],
            mic_orig_pixel_size=[1.0],
            voltage=[300.0],
            cs=[2.7],
            amplitude_contrast=[0.1],
        ),
        micrographs=MicrographsStarModel.Micrographs(
            mic_name=[
                "MotionCorr/job001/Movies/Frame_01.mrc",
                "MotionCorr/job001/Movies/Frame_02.mrc",
                "MotionCorr/job001/Movies/Frame_03.mrc",
            ],
            optics_group=[1, 1, 1],
        ),
    )
    mcor_obj.write_text("corrected_micrographs.star", m.to_string())
