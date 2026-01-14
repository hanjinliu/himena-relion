from typing import Callable
from pathlib import Path
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._pick import QManualPickViewer, QLoGPickViewer
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
    assert tester.widget._mic_list.item(0, 1).text() == "0"
    assert tester.widget._mic_list.item(1, 1).text() == "0"
    assert tester.widget._mic_list.item(2, 1).text() == "0"

    m = CoordsModel(x=[12, 15, 14], y=[3, 21, 3])
    tester.write_text("Movies/Frame_01_manualpick.star", m.to_string())

    assert tester.widget._mic_list.rowCount() == 3
    assert tester.widget._mic_list.item(0, 1).text() == "3"
    assert tester.widget._mic_list.item(1, 1).text() == "0"
    assert tester.widget._mic_list.item(2, 1).text() == "0"

    tester.widget._mic_list.set_current_row(1)

    m = CoordsModel(x=[12, 15, 14, 30], y=[3, 21, 3, 18])
    tester.write_text("Movies/Frame_02_manualpick.star", m.to_string())

    assert tester.widget._mic_list.rowCount() == 3
    assert tester.widget._mic_list.item(0, 1).text() == "3"
    assert tester.widget._mic_list.item(1, 1).text() == "4"
    assert tester.widget._mic_list.item(2, 1).text() == "0"

    assert tester.widget._mic_list.currentRow() == 1

    m = CoordsModel(x=[5], y=[12])
    tester.write_text("Movies/Frame_03_manualpick.star", m.to_string())

    assert tester.widget._mic_list.rowCount() == 3
    assert tester.widget._mic_list.item(0, 1).text() == "3"
    assert tester.widget._mic_list.item(1, 1).text() == "4"
    assert tester.widget._mic_list.item(2, 1).text() == "1"

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
    assert tester.widget._mic_list.item(0, 1).text() == "0"
    assert tester.widget._mic_list.item(1, 1).text() == "0"
    assert tester.widget._mic_list.item(2, 1).text() == "0"

    m = CoordsModel(x=[12, 15, 14], y=[3, 21, 3])
    tester.write_text("Movies/Frame_01_autopick.star", m.to_string())

    assert tester.widget._mic_list.rowCount() == 3
    assert tester.widget._mic_list.item(0, 1).text() == "3"
    assert tester.widget._mic_list.item(1, 1).text() == "0"
    assert tester.widget._mic_list.item(2, 1).text() == "0"

    tester.widget._mic_list.set_current_row(1)

    m = CoordsModel(x=[12, 15, 14, 30], y=[3, 21, 3, 18])
    tester.write_text("Movies/Frame_02_autopick.star", m.to_string())

    assert tester.widget._mic_list.rowCount() == 3
    assert tester.widget._mic_list.item(0, 1).text() == "3"
    assert tester.widget._mic_list.item(1, 1).text() == "4"
    assert tester.widget._mic_list.item(2, 1).text() == "0"

    assert tester.widget._mic_list.currentRow() == 1

    m = CoordsModel(x=[5], y=[12])
    tester.write_text("Movies/Frame_03_autopick.star", m.to_string())

    assert tester.widget._mic_list.rowCount() == 3
    assert tester.widget._mic_list.item(0, 1).text() == "3"
    assert tester.widget._mic_list.item(1, 1).text() == "4"
    assert tester.widget._mic_list.item(2, 1).text() == "1"

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
