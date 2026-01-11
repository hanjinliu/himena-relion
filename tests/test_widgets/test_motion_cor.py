from typing import Callable
from qtpy.QtWidgets import QApplication
from pathlib import Path
import numpy as np
from himena_relion._job_dir import JobDirectory
from himena_relion.testing import JobWidgetTester

def test_motioncor_spa_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    from himena_relion.relion5.widgets._frames import QMotionCorrViewer
    star_text = Path(jobs_dir_spa / "MotionCorr" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "MotionCorr")

    tester = JobWidgetTester(QMotionCorrViewer(job_dir), job_dir)

    qtbot.addWidget(tester.widget)
    assert tester.widget._mic_list.rowCount() == 0

    job_dir.path.joinpath("Movies").mkdir()
    for i in range(3):
        basename = f"Frame_{i:02d}"
        tester.write_random_mrc(f"Movies/{basename}.mrc", (40, 40), dtype=np.float16)
        tester.write_text(f"Movies/{basename}.log", "log ...")
        tester.write_text(f"Movies/{basename}.star", "star ...")
        tester.write_random_mrc(f"Movies/{basename}_PS.mrc", (10, 10), dtype=np.float16)

        assert tester.widget._mic_list.rowCount() == i + 1

    tester.widget._filter_widget.set_params(4, 20)

TILT_SERIES_STAR_TXT = """
# version 50001

data_global

loop_
_rlnTomoName #1
_rlnTomoTiltSeriesStarFile #2
_rlnVoltage #3
_rlnSphericalAberration #4
_rlnAmplitudeContrast #5
_rlnMicrographOriginalPixelSize #6
_rlnTomoHand #7
_rlnOpticsGroupName #8
TS_01	Import/job001/tilt_series/TS_01.star	300.0	2.7	0.1	0.6	-1	optics1
TS_02	Import/job001/tilt_series/TS_02.star	300.0	2.7	0.1	0.6	-1	optics1
TS_03	Import/job001/tilt_series/TS_03.star	300.0	2.7	0.1	0.6	-1	optics1
"""

TS_XX_STAR_TXT = """
# version 50001

data_TS_0{i}

loop_
_rlnMicrographMovieName #1
_rlnTomoTiltMovieFrameCount #2
_rlnTomoNominalStageTiltAngle #3
_rlnTomoNominalTiltAxisAngle #4
_rlnMicrographPreExposure #5
_rlnTomoNominalDefocus #6
frames/TS_0{i}_000_0.0.mrc	 8	  0.0 85.0	 0.0 -4.0
frames/TS_0{i}_001_40.0.mrc	 8	 40.1 85.0	30.0 -4.1
frames/TS_0{i}_002_-40.0.mrc 8	-39.9 85.0	60.0 -4.2

"""

def test_motioncor_tomo_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    from himena_relion.relion5_tomo.widgets._tilt_series import QMotionCorrViewer

    mcor_text = Path(jobs_dir_tomo / "MotionCorr" / "job001" / "job.star").read_text()
    lines = []
    for line in mcor_text.splitlines():
        if line.strip().startswith("input_star_mics"):
            line = "input_star_mics   Import/job001/tilt_series.star"
        lines.append(line)
    job_dir = make_job_directory("\n".join(lines), "MotionCorr")

    prev_job = make_job_directory(
        Path(jobs_dir_tomo / "Import" / "job001" / "job.star").read_text(),
        "Import/job001"
    )
    importjob = JobWidgetTester.no_widget(prev_job)
    importjob.mkdir("tilt_series")
    importjob.write_text("tilt_series/TS_01.star", TS_XX_STAR_TXT.format(i=1))
    importjob.write_text("tilt_series/TS_02.star", TS_XX_STAR_TXT.format(i=2))
    importjob.write_text("tilt_series/TS_03.star", TS_XX_STAR_TXT.format(i=3))
    importjob.write_text("tilt_series.star", TILT_SERIES_STAR_TXT)

    tester = JobWidgetTester(QMotionCorrViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)
    tester.widget._update_min_interval = 0.0
    assert tester.widget._ts_list.rowCount() == 0
    job_dir.path.joinpath("tilt_series").mkdir()
    job_dir.path.joinpath("frames").mkdir()
    for i in range(3):
        for i_tilt, tilt in enumerate(["0_0", "40_0", "-40_0"]):
            basename = f"TS_{i+1:02d}_{i_tilt:03d}_{tilt}"
            tester.write_random_mrc(f"frames/{basename}.mrc", (40, 40), dtype=np.float16)
            tester.write_text(f"frames/{basename}.log", "log ...")
            tester.write_text(f"frames/{basename}.star", "star ...")
            tester.write_random_mrc(f"frames/{basename}_PS.mrc", (10, 10), dtype=np.float16)
        assert tester.widget._ts_list.rowCount() == i + 1
    assert tester.widget._ts_list.rowCount() == 3
    tester.widget._ts_list.setCurrentCell(0, 0)
    QApplication.processEvents()
    tester.widget._ts_list.setCurrentCell(1, 0)
    QApplication.processEvents()
    tester.widget._ts_list.setCurrentCell(2, 0)
    QApplication.processEvents()
    tester.widget._filter_widget.set_params(4, 20)
