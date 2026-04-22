from typing import Callable
from pathlib import Path
from starfile_rs import as_star
import polars as pl
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._ctf import QCtfFindViewer, QCtfRefineAnisoMagViewer
from himena_relion.testing import JobWidgetTester

_PS_FORMAT = """# Output from CTFFind version 4.1.14, run on 2025-12-28 18:56:33
# Input file: CtfFind/job003/Movies/XXX_PS.mrc ; Number of micrographs: 1
# Pixel size: 1.400 Angstroms ; acceleration voltage: 200.0 keV ; spherical aberration: 1.40 mm ; amplitude contrast: 0.10
# Box size: 512 pixels ; min. res.: 30.0 Angstroms ; max. res.: 5.0 Angstroms ; min. def.: 5000.0 um; max. def. 50000.0 um
# Columns: #1 - micrograph number; #2 - defocus 1 [Angstroms]; #3 - defocus 2; #4 - azimuth of astigmatism; #5 - additional phase shift [radians]; #6 - cross correlation; #7 - spacing (in Angstroms) up to which CTF rings were fit successfully
1.000000 10864.138672 10575.676758 78.283111 0.000000 0.131144 4.874623
"""

def test_ctffind(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "CtfFind" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "CtfFind")

    tester = JobWidgetTester(QCtfFindViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    tester.widget._update_min_interval = 0.0
    tester.mkdir("Movies")

    tester.write_text("Movies/A01_PS.txt", _PS_FORMAT)
    tester.write_random_mrc("Movies/A01_PS.ctf", (64, 64))
    assert tester.widget._viewer.has_image
    tester.write_text("Movies/A02_PS.txt", _PS_FORMAT)
    tester.write_random_mrc("Movies/A02_PS.ctf", (64, 64))

    df = pl.DataFrame(
        {
            "micrograph_number": [1, 2],
            "rlnDefocusU": [10864, 10864],
            "rlnDefocusV": [10575, 10575],
            "rlnDefocusAngle": [78.2, 78.2],
            "phase_shift": [0.0, 0.0],
            "rlnCtfFigureOfMerit": [0.144, 0.187],
            "rlnCtfMaxResolution": [4.94, 2.33],
        }
    )
    tester.write_text("micrograph_ctf.star", as_star({"micrograph": df}).to_string())

def test_ctfrefine_aniso_mag(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "CtfRefine" / "job002" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "CtfRefine")

    tester = JobWidgetTester(QCtfRefineAnisoMagViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    df_opt = pl.DataFrame(
        {
            "rlnOpticsGroupName": ["group1", "group2"],
            "rlnOpticsGroup": [1, 2],
        }
    )
    tester.write_text(
        "particles_ctf_refine.star", as_star({"optics": df_opt}).to_string()
    )

    for index in df_opt["rlnOpticsGroup"]:
        path_x_obs = job_dir.path / f"mag_disp_x_optics-group_{index}.mrc"
        path_y_obs = job_dir.path / f"mag_disp_y_optics-group_{index}.mrc"
        path_x_fit = job_dir.path / f"mag_disp_x_fit_optics-group_{index}.mrc"
        path_y_fit = job_dir.path / f"mag_disp_y_fit_optics-group_{index}.mrc"
        tester.write_random_mrc(path_x_obs, (64, 64))
        tester.write_random_mrc(path_y_obs, (64, 64))
        tester.write_random_mrc(path_x_fit, (64, 64))
        tester.write_random_mrc(path_y_fit, (64, 64))

    tester.widget._process_update()
