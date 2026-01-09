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
        tester.write_random_mrc(f"Movies/{basename}.mrc", (10, 10), dtype=np.float16)
        tester.write_text(f"Movies/{basename}.log", "log ...")
        tester.write_text(f"Movies/{basename}.star", "star ...")
        tester.write_random_mrc(f"Movies/{basename}_PS.mrc", (10, 3), dtype=np.float16)

        assert tester.widget._mic_list.rowCount() == i + 1

    for _ in range(3):
        QApplication.processEvents()

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
_rlnTomoTiltSeriesPixelSize #9
     TS_01 MotionCorr/job001/tilt_series/TS_01.star   300.000000     2.700000     0.100000     0.675000     -1.00000    optics1     1.350000
     TS_02 MotionCorr/job001/tilt_series/TS_02.star   300.000000     2.700000     0.100000     0.675000     -1.00000    optics1     1.350000
     TS_03 MotionCorr/job001/tilt_series/TS_03.star   300.000000     2.700000     0.100000     0.675000     -1.00000    optics1     1.350000

"""

TS_XX_STAR_TXT = """
# version 50001

data_TS_01

loop_
_rlnMicrographMovieName #1
_rlnTomoTiltMovieFrameCount #2
_rlnTomoNominalStageTiltAngle #3
_rlnTomoNominalTiltAxisAngle #4
_rlnMicrographPreExposure #5
_rlnTomoNominalDefocus #6
_rlnCtfPowerSpectrum #7
_rlnMicrographNameEven #8
_rlnMicrographNameOdd #9
_rlnMicrographName #10
_rlnMicrographMetadata #11
_rlnAccumMotionTotal #12
_rlnAccumMotionEarly #13
_rlnAccumMotionLate #14
frames/TS_0{i}_000_0.0.mrc    8 0.001000 85.0 0.0 -4.0 MotionCorr/job025/frames/TS_0{i}_000_0_0_PS.mrc MotionCorr/job025/frames/TS_0{i}_000_0_0_EVN.mrc MotionCorr/job025/frames/TS_0{i}_000_0_0_ODD.mrc MotionCorr/job025/frames/TS_0{i}_000_0_0.mrc MotionCorr/job025/frames/TS_0{i}_000_0_0.star 2.297631 1.0 1.289649
frames/TS_0{i}_001_40.0.mrc   8 3.001130 85.0 3.0 -4.0 MotionCorr/job025/frames/TS_0{i}_001_40_0_PS.mrc MotionCorr/job025/frames/TS_0{i}_001_40_0_EVN.mrc MotionCorr/job025/frames/TS_0{i}_001_3_0_ODD.mrc MotionCorr/job025/frames/TS_0{i}_001_40_0.mrc MotionCorr/job025/frames/TS_0{i}_001_40_0.star 2.384960 0.0 2.384960
frames/TS_0{i}_002_-40.0.mrc  8 -2.99863 85.0 6.0 -4.0 MotionCorr/job025/frames/TS_0{i}_002_-40_0_PS.mrc MotionCorr/job025/frames/TS_0{i}_002_-40_0_EVN.mrc MotionCorr/job025/frames/TS_0{i}_002_-3_0_ODD.mrc MotionCorr/job025/frames/TS_0{i}_002_-40_0.mrc MotionCorr/job025/frames/TS_0{i}_001_-40_0.star 2.008728 0.0 2.008728
"""

def test_motioncor_tomo_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_tomo,
):
    from himena_relion.relion5_tomo.widgets._tilt_series import QMotionCorrViewer

    star_text = Path(jobs_dir_tomo / "MotionCorr" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "MotionCorr")

    tester = JobWidgetTester(QMotionCorrViewer(job_dir), job_dir)

    qtbot.addWidget(tester.widget)
    assert tester.widget._ts_list.rowCount() == 0
    job_dir.path.joinpath("tilt_series").mkdir()
    job_dir.path.joinpath("frames").mkdir()
    for i in range(3):
        for i_tilt, tilt in enumerate(["0_0", "40_0", "-40_0"]):
            basename = f"TS_{i+1:02d}_{i_tilt:03d}_{tilt}"
            tester.write_random_mrc(f"frames/{basename}.mrc", (10, 10), dtype=np.float16)
            tester.write_text(f"frames/{basename}.log", "log ...")
            tester.write_text(f"frames/{basename}.star", "star ...")
            tester.write_random_mrc(f"frames/{basename}_PS.mrc", (10, 3), dtype=np.float16)

        tester.write_text(
            f"tilt_series/TS_{i+1:02d}.star",
            TS_XX_STAR_TXT.format(i=i + 1)
        )
    tester.write_text("corrected_tilt_series.star", TILT_SERIES_STAR_TXT)
    assert tester.widget._ts_list.rowCount() == 3
    tester.widget._ts_list.setCurrentCell(0, 0)
    QApplication.processEvents()
    tester.widget._ts_list.setCurrentCell(1, 0)
    QApplication.processEvents()
    tester.widget._ts_list.setCurrentCell(2, 0)
    QApplication.processEvents()
