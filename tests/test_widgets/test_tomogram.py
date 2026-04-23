from typing import Callable
from pathlib import Path
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5_tomo.widgets._aligntilt import aligntilt_viewer, QAreTomo2TomogramViewer
from himena_relion.relion5_tomo.widgets._tomogram import QTomogramViewer, QDenoiseTrainViewer, QDenoiseTomogramViewer
from himena_relion.testing import JobWidgetTester

def test_reconstruct_tomo_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    star_text = Path(jobs_dir_tomo / "Tomogram" / "job001" / "job.star").read_text()
    star_text = _replace_is_halfset(star_text, False)
    job_dir = make_job_directory(star_text, "Tomogram")

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

    tester.widget._tomo_list.set_current_row(1)

def test_reconstruct_by_aretomo_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    star_text = Path(jobs_dir_tomo / "AlignTiltSeries" / "job004" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "AlignTiltSeries")

    tester = JobWidgetTester(aligntilt_viewer(job_dir), job_dir)
    assert isinstance(tester.widget, QAreTomo2TomogramViewer)
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

    tester.widget._tomo_list.set_current_row(1)


def test_reconstruct_tomo_widget_halfsets(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    star_text = Path(jobs_dir_tomo / "Tomogram" / "job001" / "job.star").read_text()
    star_text = _replace_is_halfset(star_text, True)
    job_dir = make_job_directory(star_text, "Tomogram")

    tester = JobWidgetTester(QTomogramViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)
    assert not tester.widget._viewer.has_image

    tester.mkdir("tomograms")
    assert not tester.widget._viewer.has_image
    assert tester.widget._tomo_list.rowCount() == 0

    tester.write_random_mrc("tomograms/rec_TS_01_half1.mrc", (40, 100, 100))
    assert tester.widget._viewer.has_image
    tester.write_random_mrc("tomograms/rec_TS_01_half2.mrc", (40, 100, 100))
    assert tester.widget._viewer.has_image
    assert tester.widget._tomo_list.rowCount() == 1
    assert tester.widget._tomo_list.current_text() == "TS_01"

    tester.write_random_mrc("tomograms/rec_TS_02_half1.mrc", (40, 100, 100))
    tester.write_random_mrc("tomograms/rec_TS_02_half2.mrc", (40, 100, 100))
    assert tester.widget._viewer.has_image
    assert tester.widget._tomo_list.rowCount() == 2
    assert tester.widget._tomo_list.current_text() == "TS_01"

    tester.widget._tomo_list.set_current_row(1)

def test_denoise_train_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    import tarfile
    import pickle
    from io import BytesIO

    star_text = Path(jobs_dir_tomo / "Denoise" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "Denoise")

    tester = JobWidgetTester(QDenoiseTrainViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    hist = {
        "loss": [1.0, 0.8, 0.6],
        "mae": [0.5, 0.4, 0.3],
        "mse": [0.25, 0.16, 0.09],
        "val_loss": [1.1, 0.9, 0.7],
        "val_mae": [0.55, 0.45, 0.35],
        "val_mse": [0.3, 0.2, 0.1],
    }

    with tarfile.open(tester.job_dir.path / "denoising_model.tar.gz", "w:gz") as tar:
        hist_bytes = pickle.dumps(hist)
        infodir = tarfile.TarInfo(name="denoising_model/")
        infodir.type = tarfile.DIRTYPE
        tar.addfile(infodir)
        tarinfo = tarfile.TarInfo(name="denoising_model/history.dat")
        tarinfo.size = len(hist_bytes)
        tar.addfile(tarinfo, fileobj=BytesIO(hist_bytes))

    tester.initialize()

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

    tester.widget._tomo_list.set_current_row(1)

def _replace_is_halfset(star_text: str, is_halfset: bool) -> str:
    lines = []
    value = "Yes" if is_halfset else "No"
    for line in star_text.splitlines():
        if line.strip().startswith("generate_split_tomograms"):
            line = f"generate_split_tomograms   {value}"
        lines.append(line)
    star_text = "\n".join(lines)
    return star_text
