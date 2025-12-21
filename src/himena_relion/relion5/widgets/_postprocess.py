from __future__ import annotations
from pathlib import Path
import logging
from superqt import QToggleSwitch
from himena_relion._widgets import (
    QJobScrollArea,
    QPlotCanvas,
    register_job,
    Q3DViewer,
    spacer_widget,
)
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


@register_job(_job_dir.PostProcessJobDirectory)
class QPostProcessViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._viewer = Q3DViewer()
        self._viewer.setMaximumSize(400, 400)
        self._use_mask = QToggleSwitch("Show masked map")
        self._use_mask.setChecked(False)
        self._canvas = QPlotCanvas(self)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(self._use_mask)
        self._layout.addWidget(self._canvas)
        self._layout.addWidget(spacer_widget())
        self._job_dir: _job_dir.PostProcessJobDirectory | None = None
        self._use_mask.toggled.connect(self._on_use_mask_toggled)

    def on_job_updated(self, job_dir: _job_dir.PostProcessJobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix not in [".out", ".err"]:
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", self._job_dir.job_id)

    def initialize(self, job_dir: _job_dir.PostProcessJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        img = job_dir.map_mrc(masked=self._use_mask.isChecked())
        if img is not None:
            self._viewer.set_image(img, update_now=False)
            self._viewer.auto_threshold(update_now=False)
            self._viewer.auto_fit()

        df_fsc = job_dir.fsc_dataframe()
        if df_fsc is not None:
            self._canvas.plot_fsc_postprocess(df_fsc)

    def _on_use_mask_toggled(self, *_):
        """Handle toggling between masked and unmasked maps."""
        if self._job_dir is not None:
            self.initialize(self._job_dir)
