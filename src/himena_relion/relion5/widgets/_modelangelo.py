from __future__ import annotations
from pathlib import Path
import logging
import mrcfile
from cmap import Colormap
import polars as pl
from starfile_rs import read_star
from himena_relion._widgets import (
    QJobScrollArea,
    register_job,
    Q3DViewer,
    spacer_widget,
)
from himena_relion import _job_dir
from himena_relion._widgets._shared.resizer import QResizer
from vispy.scene import Line
from vispy.visuals.filters import Alpha


_LOGGER = logging.getLogger(__name__)


@register_job("modelangelo")
class QModelAngeloViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._viewer = Q3DViewer()
        alpha_filter = Alpha(0.5)
        self._viewer._canvas.image_visual.attach(alpha_filter)
        self._viewer._canvas.image_visual.set_gl_state("additive", depth_test=True)
        self._resizer = QResizer(self._viewer)
        self._layout.setSpacing(0)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(self._resizer)
        self._layout.addWidget(spacer_widget())
        self._job_dir = job_dir
        self._line_visuals: list[Line] = []

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        if Path(path).suffix in [".cif"]:
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        # show map
        if mrc_path := job_dir.get_job_param("fn_map"):
            mrc_path = job_dir.resolve_path(mrc_path)
            with mrcfile.open(mrc_path, mode="r") as mrc:
                img = mrc.data
                scale = mrc.voxel_size.x
            self._viewer.set_image(img, update_now=False)
            self._viewer.auto_threshold(update_now=False)
            self._viewer.auto_fit()
        else:
            scale = 1.0
        for line in self._line_visuals:
            line.parent = None
        self._line_visuals.clear()

        cif_path = job_dir.path / f"{job_dir.path.stem}.cif"
        colorgen = Colormap("jet")
        if cif_path.exists():
            # cif file is just a star file.
            df = read_star(cif_path).first().to_polars()
            df_ca = df.filter(pl.col("atom_site.label_atom_id") == "CA")
            ith = 0
            for _, sub in df_ca.group_by(
                "atom_site.label_asym_id", maintain_order=True
            ):
                coords = (
                    sub.select(
                        "atom_site.Cartn_x", "atom_site.Cartn_y", "atom_site.Cartn_z"
                    ).to_numpy()
                    / scale
                )
                color = colorgen((ith * 7.3) % 7 / 7)
                line = Line(
                    coords,
                    color=color.hex,
                    width=1,
                    antialias=True,
                    parent=self._viewer._canvas._viewbox.scene,
                )
                line.set_gl_state("opaque", depth_test=False)
                self._line_visuals.append(line)
                ith += 1
