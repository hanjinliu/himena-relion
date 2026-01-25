from __future__ import annotations
from pathlib import Path
import mrcfile
from qtpy import QtWidgets as QtW
import logging
from himena_relion._widgets import (
    QJobScrollArea,
    register_job,
    Q3DViewer,
)
from himena_relion import _job_dir
from himena_relion.consts import RelionNodeTypeLabels


_LOGGER = logging.getLogger(__name__)

# "Particle coordinates (*.box, *_pick.star)",
# "Particles STAR file (*.star)",
# "Multiple (2D or 3D) references (.star or .mrcs)",
# "3D reference (.mrc)",
# "3D mask (.mrc)",
# "Unfiltered half-map (unfil.mrc)",


@register_job("relion.import.other")
class QImportOthersJob(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        self._initialized = False
        self._top_label = QtW.QLabel("Nothing imported yet.")
        self._layout.addWidget(self._top_label)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        if self._initialized:
            return
        pipeline = job_dir.parse_job_pipeline()
        outputs = pipeline.outputs
        if len(outputs) == 0:
            return
        output = outputs[0]
        if tp := output.type_label:
            if tp.startswith(RelionNodeTypeLabels.DENSITY_MAP):
                self._init_density_map(output.path)
            elif tp.startswith(RelionNodeTypeLabels.MASK):
                self._init_density_map(output.path)
            else:
                pass
            node_type = job_dir.get_job_param("node_type")
            self._top_label.setText(f"<b>Imported File = {node_type}</b>")
            self._initialized = True

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix not in [".out", ".err"]:
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def _init_density_map(self, path):
        layout = self._layout
        self._viewer = Q3DViewer()
        layout.addWidget(self._viewer)
        mrc_path = self._job_dir.resolve_path(path)
        if mrc_path.exists():
            with mrcfile.open(mrc_path, mode="r") as mrc:
                img = mrc.data
            self._viewer.set_image(img)
            self._viewer.auto_threshold()
            self._viewer.auto_fit()
