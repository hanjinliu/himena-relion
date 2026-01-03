from __future__ import annotations
from pathlib import Path
import logging
import numpy as np
from qtpy import QtWidgets as QtW
import mrcfile
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DLocalResViewer,
    register_job,
)
from himena_relion import _job_dir, _utils

_LOGGER = logging.getLogger(__name__)


@register_job("relion.localres")
class QLocalResViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        layout = self._layout
        self._viewer = Q3DLocalResViewer()
        layout.addWidget(QtW.QLabel("<b>Local Resolution Map</b>"))
        layout.addWidget(self._viewer)
        self._job_dir = job_dir

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.name.endswith("_locres.mrc"):
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        map_data, locres_data, mask_data, scale = _read_files(job_dir)
        cutoff_angst = np.min(locres_data[locres_data > 0.001])
        cutoff_rel = map_data.shape[0] * scale / cutoff_angst
        print(cutoff_angst, cutoff_rel)
        map_filtered = _utils.lowpass_filter(map_data, cutoff_rel)
        self._viewer.set_images(map_filtered, locres_data, mask_data)


def _read_mrc(path: Path) -> tuple[np.ndarray, float]:
    with mrcfile.open(path) as mrc:
        data = mrc.data.copy()
        scale = mrc.voxel_size.x
    return data, float(scale)


def _read_files(
    job_dir: _job_dir.JobDirectory,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, float]:
    locres_path = job_dir.path / "relion_locres.mrc"
    params = job_dir.get_job_params_as_dict()
    map_path = job_dir.resolve_path(params["fn_in"])
    map_data, scale = _read_mrc(map_path)
    locres_data, _ = _read_mrc(locres_path)
    if mask_path_rel := params.get("fn_mask", ""):
        mask_path = job_dir.resolve_path(mask_path_rel)
        mask_data, _ = _read_mrc(mask_path)
    else:
        mask_data = None
    return map_data, locres_data, mask_data, scale
