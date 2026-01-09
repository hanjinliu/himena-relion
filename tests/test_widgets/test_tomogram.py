from typing import Callable
from pathlib import Path
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5_tomo.widgets._tomogram import QTomogramViewer, QDenoiseTomogramViewer
from himena_relion.testing import JobWidgetTester

def test_reconstruct_tomo_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    star_text = Path(jobs_dir_tomo / "Tomogram" / "job001" / "job.star").read_text()
    _replace_is_halfset(star_text, False)
    job_dir = make_job_directory(star_text, "Refine3D")

    tester = JobWidgetTester(QTomogramViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)
    assert not tester.widget._viewer.has_image

    tester.mkdir("tomograms")
    assert not tester.widget._viewer.has_image
    assert tester.widget._tomo_list.rowCount() == 0

    tester.write_random_mrc("tomograms/rec_TS_01.mrc", (40, 100, 100))
    assert tester.widget._viewer.has_image
    assert tester.widget._tomo_list.rowCount() == 1
    assert tester.widget._tomo_list.current_text() == "TS_01"

    tester.write_random_mrc("tomograms/rec_TS_02.mrc", (40, 100, 100))
    assert tester.widget._viewer.has_image
    assert tester.widget._tomo_list.rowCount() == 2
    assert tester.widget._tomo_list.current_text() == "TS_01"

    tester.widget._tomo_list.setCurrentCell(1, 0)

def test_reconstruct_tomo_widget_halfsets(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    star_text = Path(jobs_dir_tomo / "Tomogram" / "job001" / "job.star").read_text()
    _replace_is_halfset(star_text, True)
    job_dir = make_job_directory(star_text, "Tomogram")

    tester = JobWidgetTester(QTomogramViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)
    assert not tester.widget._viewer.has_image

    tester.mkdir("tomograms")
    assert not tester.widget._viewer.has_image
    assert tester.widget._tomo_list.rowCount() == 0

    tester.write_random_mrc("tomograms/rec_TS_01_half1.mrc", (40, 100, 100))
    assert not tester.widget._viewer.has_image
    tester.write_random_mrc("tomograms/rec_TS_01_half2.mrc", (40, 100, 100))
    assert tester.widget._viewer.has_image
    assert tester.widget._tomo_list.rowCount() == 1
    assert tester.widget._tomo_list.current_text() == "TS_01"

    tester.write_random_mrc("tomograms/rec_TS_02_half1.mrc", (40, 100, 100))
    tester.write_random_mrc("tomograms/rec_TS_02_half2.mrc", (40, 100, 100))
    assert tester.widget._viewer.has_image
    assert tester.widget._tomo_list.rowCount() == 2
    assert tester.widget._tomo_list.current_text() == "TS_01"

    tester.widget._tomo_list.setCurrentCell(1, 0)

def test_denoise_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    star_text = Path(jobs_dir_tomo / "Denoise" / "job002" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Denoise")

    tester = JobWidgetTester(QDenoiseTomogramViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)
    assert not tester.widget._viewer.has_image

    tester.mkdir("tomograms")
    assert not tester.widget._viewer.has_image
    assert tester.widget._tomo_list.rowCount() == 0

    tester.write_random_mrc("tomograms/rec_TS_01.mrc", (40, 100, 100))
    assert tester.widget._tomo_list.rowCount() == 1
    assert tester.widget._tomo_list.current_text() == "TS_01"
    assert tester.widget._viewer.has_image

    tester.write_random_mrc("tomograms/rec_TS_02.mrc", (40, 100, 100))
    assert tester.widget._tomo_list.rowCount() == 2
    assert tester.widget._tomo_list.current_text() == "TS_01"
    assert tester.widget._viewer.has_image

    tester.widget._tomo_list.setCurrentCell(1, 0)

def _replace_is_halfset(star_text: str, is_halfset: bool) -> str:
    lines = []
    value = "Yes" if is_halfset else "No"
    for line in star_text.splitlines():
        if line.strip().startswith("generate_split_tomograms"):
            line = f"generate_split_tomograms   {value}"
        lines.append(line)
    star_text = "\n".join(lines)
    return star_text
