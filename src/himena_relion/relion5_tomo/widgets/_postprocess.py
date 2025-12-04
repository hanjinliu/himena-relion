from __future__ import annotations
from pathlib import Path

from himena_relion._widgets import QJobScrollArea, QPlotCanvas, register_job
from himena_relion import _job


@register_job(_job.PostProcessJobDirectory)
class QMaskCreateViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._canvas = QPlotCanvas()
        self._layout.addWidget(self._canvas)

    def on_job_updated(self, job_dir: _job.PostProcessJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix not in [".out", ".err"]:
            self.initialize(job_dir)

    def initialize(self, job_dir: _job.PostProcessJobDirectory):
        """Initialize the viewer with the job directory."""
        self._canvas.plot_fsc_postprocess(job_dir.fsc_dataframe())
