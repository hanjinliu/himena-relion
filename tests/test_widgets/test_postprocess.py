from typing import Callable
from pathlib import Path
from himena_relion._job_dir import JobDirectory
from himena_relion.relion5.widgets._postprocess import QPostProcessViewer
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

POSTPROCESS_STAR = """
# version 50001

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
"""
