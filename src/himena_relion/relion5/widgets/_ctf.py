from __future__ import annotations
from pathlib import Path
import logging
import numpy as np
from numpy.typing import NDArray
from typing import Any, Callable
import pandas as pd
from qtpy import QtWidgets as QtW
from superqt.utils import thread_worker, GeneratorWorker
from starfile_rs import read_star
from himena_relion._image_readers._array import ArrayFilteredView
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    QPlotCanvas,
    register_job,
)
from himena_relion import _job_dir
from ._shared import QMicrographListWidget

_LOGGER = logging.getLogger(__name__)


def read_ctf_output_txt(path: Path) -> NDArray[np.float32]:
    """Read a CTF output text file into a MicrographsModel."""
    # Each column:
    # micrograph number
    # defocus 1
    # defocus 2
    # azimuth of astigmatism
    # additional phase shift
    # cross correlation
    # spacing (A) up to which CTF ring were fit successfully = max resolution
    return np.loadtxt(path, dtype=np.float32)


@register_job("relion.ctffind.ctffind4", is_tomo=True)
class QCtfFindViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = _job_dir.CtfCorrectionJobDirectory(job_dir.path)
        self._worker: GeneratorWorker | None = None
        layout = self._layout
        self._defocus_canvas = QPlotCanvas(self)
        self._defocus_canvas.setFixedSize(360, 145)
        self._astigmatism_canvas = QPlotCanvas(self)
        self._astigmatism_canvas.setFixedSize(360, 145)
        self._defocus_angle_canvas = QPlotCanvas(self)
        self._defocus_angle_canvas.setFixedSize(360, 145)
        self._max_resolution_canvas = QPlotCanvas(self)
        self._max_resolution_canvas.setFixedSize(360, 145)

        self._mic_list = QMicrographListWidget()
        self._mic_list.current_changed.connect(self._mic_changed)

        self._viewer = Q2DViewer(zlabel="Tilt index")
        splitter = QtW.QSplitter()
        splitter.addWidget(self._mic_list)
        splitter.addWidget(self._viewer)
        layout.addWidget(QtW.QLabel("<b>Defocus</b>"))
        layout.addWidget(self._defocus_canvas)
        layout.addWidget(QtW.QLabel("<b>Astigmatism</b>"))
        layout.addWidget(self._astigmatism_canvas)
        layout.addWidget(QtW.QLabel("<b>Defocus angle</b>"))
        layout.addWidget(self._defocus_angle_canvas)
        layout.addWidget(QtW.QLabel("<b>Max resolution</b>"))
        layout.addWidget(self._max_resolution_canvas)
        layout.addWidget(QtW.QLabel("<b>CTF spectra</b>"))
        layout.addWidget(splitter)
        splitter.setSizes([200, 400])

    def on_job_updated(self, job_dir, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".ctf":
            self._process_update()
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def initialize(self, job_dir):
        """Initialize the viewer with the job directory."""
        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        if self._job_dir.path.joinpath("Movies").exists():
            if self._worker is not None:
                self._worker.quit()
            self._worker = self._prep_data_to_plot(self._job_dir)
            self._worker.yielded.connect(self._on_data_ready)
            self._worker.start()
        else:
            # clear everything
            self._defocus_canvas.clear()
            self._astigmatism_canvas.clear()
            self._defocus_angle_canvas.clear()
            self._max_resolution_canvas.clear()
            self._viewer.clear()

    @thread_worker
    def _prep_data_to_plot(self, job_dir: _job_dir.JobDirectory):
        if (final_path := job_dir.path.joinpath("micrographs_ctf.star")).exists():
            df = read_star(final_path).get("micrographs").trust_loop().to_pandas()
        else:
            mov_dir = job_dir.path.joinpath("Movies")
            if not mov_dir.exists():
                return
            it = mov_dir.glob("*_frameImage_PS.txt")
            arr = np.stack([read_ctf_output_txt(txtpath) for txtpath in it])
            df = pd.DataFrame(
                arr,
                columns=[
                    "micrograph_number",
                    "rlnDefocusU",
                    "rlnDefocusV",
                    "rlnDefocusAngle",
                    "phase_shift",
                    "rlnCtfFigureOfMerit",
                    "rlnCtfMaxResolution",
                ],
            )
        yield self._defocus_canvas.plot_defocus, df
        yield self._astigmatism_canvas.plot_ctf_astigmatism, df
        yield self._defocus_angle_canvas.plot_ctf_defocus_angle, df
        yield self._max_resolution_canvas.plot_ctf_max_resolution, df
        ctf_paths = [(f.name,) for f in mov_dir.glob("*_frameImage_PS.ctf")]
        yield self._update_ctf_choices, ctf_paths

        self._worker = None

    def _on_data_ready(self, yielded: tuple[Callable, Any]):
        fn, df = yielded
        fn(df)

    def _update_ctf_choices(self, mic_names: list[tuple[str]]):
        """Update the micrograph choices in the list widget."""
        self._mic_list.set_choices(mic_names)

    def _mic_changed(self, row: tuple[str]):
        """Handle changes to selected micrograph."""
        mic_path = self._job_dir.path / "Movies" / row[0]
        movie_view = ArrayFilteredView.from_mrc(mic_path)
        had_image = self._viewer.has_image
        self._viewer.set_array_view(
            movie_view,
            clim=self._viewer._last_clim,
        )
        if not had_image:
            self._viewer._auto_contrast()

    def widget_added_callback(self):
        self._defocus_canvas.widget_added_callback()
        self._astigmatism_canvas.widget_added_callback()
        self._defocus_angle_canvas.widget_added_callback()
        self._max_resolution_canvas.widget_added_callback()

    def closeEvent(self, a0):
        self.widget_closed_callback()
        return super().closeEvent(a0)

    def widget_closed_callback(self):
        if self._worker is not None:
            self._worker.quit()
            self._worker = None
