from typing import Callable
from pathlib import Path
import mrcfile
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._postprocess import QPostProcessViewer
from himena_relion.relion5.widgets._mask_create import QMaskCreateViewer
from himena_relion.testing import JobWidgetTester

def test_postprocess_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "PostProcess" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "PostProcess")

    tester = JobWidgetTester(QPostProcessViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    tester.write_random_mrc("postprocess.mrc", shape=(32, 32, 32))
    tester.write_random_mrc("postprocess_masked.mrc", shape=(32, 32, 32))
    tester.write_text("postprocess.star", POSTPROCESS_STAR)
    tester.widget._use_mask.setChecked(True)
    tester.widget._use_mask.setChecked(False)

def test_postprocess_widget_retry(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "PostProcess" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "PostProcess")

    tester = JobWidgetTester(QPostProcessViewer(job_dir), job_dir)
    widget = tester.widget
    qtbot.addWidget(widget)
    timer = widget._retry_timer
    fp = job_dir.path / "postprocess_masked.mrc"
    with mrcfile.new(fp) as mrc:
        mrc.set_data(tester.make_random_mrc((32, 32, 32)))
    content = fp.read_bytes()

    # file is not completely written yet
    fp.write_bytes(content[: len(content) // 2])
    widget.on_job_updated(job_dir, str(fp))
    assert not widget._viewer.has_image
    assert widget._current_map_path is None
    assert timer.isActive()

    # retried after the file is written
    fp.write_bytes(content)
    qtbot.waitUntil(lambda: widget._viewer.has_image, timeout=3000)
    assert widget._current_map_path == fp
    assert not timer.isActive()
    assert timer.num_retry == 0

    # retry stops if the file stays broken
    timer.setInterval(10)
    fp.write_bytes(content[: len(content) // 2])
    widget.on_job_updated(job_dir, str(fp))
    qtbot.waitUntil(
        lambda: timer.num_retry == timer.max_retry and not timer.isActive(),
        timeout=3000,
    )
    assert widget._viewer.has_image  # the previous map is kept

    # the pending retry is cancelled when the window is closed
    widget.on_job_updated(job_dir, str(fp))
    assert timer.isActive()
    widget.window_closed_callback()
    assert not timer.isActive()

POSTPROCESS_STAR = """
# version 50001

data_general

_rlnFinalResolution                               9.99
_rlnBfactorUsedForSharpening                      0.000000
_rlnUnfilteredMapHalf1                        Reconstruct/job032/half1.mrc
_rlnUnfilteredMapHalf2                        Reconstruct/job032/half2.mrc
_rlnPostprocessedMap                          PostProcess/job001/postprocess.mrc
_rlnParticleBoxFractionSolventMask               10.682012
_rlnMaskName                                  mask.mrc
_rlnRandomiseFrom                                 7.200000
_rlnPostprocessedMapMasked                    PostProcess/job001/postprocess_masked.mrc

data_fsc

loop_
_rlnSpectralIndex #1
_rlnResolution #2
_rlnAngstromResolution #3
_rlnFourierShellCorrelationCorrected #4
_rlnFourierShellCorrelationParticleMaskFraction #5
_rlnFourierShellCorrelationUnmaskedMaps #6
_rlnFourierShellCorrelationMaskedMaps #7
_rlnCorrectedFourierShellCorrelationPhaseRandomizedMaskedMaps #8
           0     0.001001   999.000000     1.000000     1.000000     1.000000     1.000000     1.000000
           1     0.003858   259.200012     0.999200     0.999968     0.999653     0.999200     0.999184
           2     0.007716   129.600006     0.997951     0.999928     0.999235     0.997951     0.997930
           3     0.011574    86.400004     0.999357     0.999994     0.999939     0.999357     0.999395
           4     0.015432    64.800003     0.999841     0.999993     0.999929     0.999841     0.999835
           5     0.019290    51.840002     0.999806     0.999977     0.999749     0.999806     0.999803
           6     0.023148    43.200002     0.999749     0.999956     0.999526     0.999749     0.999757

data_guinier
loop_
_rlnResolutionSquared
_rlnLogAmplitudesOriginal
_rlnLogAmplitudesWeighted
0.00 -30.00 -30.00
0.10 -9.00 -9.50
0.20 -8.00 -99.00
"""

def test_mask_create_widget(
    qtbot,
    make_job_directory: Callable[[str, str], JobDirectory],
    jobs_dir_spa,
):
    star_text = Path(jobs_dir_spa / "MaskCreate" / "job001" / "job.star").read_text()
    job_dir = make_job_directory(star_text, "MaskCreate")

    tester = JobWidgetTester(QMaskCreateViewer(job_dir), job_dir)
    qtbot.addWidget(tester.widget)

    tester.write_sphere_mrc("mask.mrc", 32)
