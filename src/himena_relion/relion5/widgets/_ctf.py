from __future__ import annotations
from pathlib import Path
import logging
import time
import mrcfile
import numpy as np
from numpy.typing import NDArray
from vispy.color import get_colormap, Colormap
import polars as pl
from qtpy import QtWidgets as QtW, QtCore
from superqt.utils import thread_worker
from starfile_rs import read_star, read_star_block
from himena_relion._image_readers._array import ArrayFilteredView
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DSimpleViewer,
    Q2DViewer,
    QPlotCanvas,
    register_job,
    QMicrographListWidget,
)
from himena_relion.schemas import OpticsModel
from himena_relion import _job_dir

_LOGGER = logging.getLogger(__name__)


def read_ctf_output_txt(path: Path) -> NDArray[np.float32] | None:
    """Read a CTF output text file into a MicrographsModel."""
    # Each column:
    # micrograph number
    # defocus 1
    # defocus 2
    # azimuth of astigmatism
    # additional phase shift
    # cross correlation
    # spacing (A) up to which CTF ring were fit successfully = max resolution
    arr = np.loadtxt(path, dtype=np.float32)
    if arr.ndim != 1 or arr.shape[0] != 7:
        return None
    return arr


@register_job("relion.ctffind.ctffind4")
class QCtfFindViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout
        self._defocus_canvas = QPlotCanvas(self)
        self._defocus_canvas.setFixedSize(360, 145)
        self._astigmatism_canvas = QPlotCanvas(self)
        self._astigmatism_canvas.setFixedSize(360, 145)
        self._defocus_angle_canvas = QPlotCanvas(self)
        self._defocus_angle_canvas.setFixedSize(360, 145)
        self._max_resolution_canvas = QPlotCanvas(self)
        self._max_resolution_canvas.setFixedSize(360, 145)

        self._mic_list = QMicrographListWidget(["CTF image", "Full Path"])
        self._mic_list.setColumnHidden(1, True)
        self._mic_list.current_changed.connect(self._mic_changed)

        self._viewer = Q2DViewer()
        layout.addWidget(QtW.QLabel("<b>Defocus U/V</b>"))
        layout.addWidget(self._defocus_canvas)
        layout.addWidget(QtW.QLabel("<b>Astigmatism</b>"))
        layout.addWidget(self._astigmatism_canvas)
        layout.addWidget(QtW.QLabel("<b>Defocus angle</b>"))
        layout.addWidget(self._defocus_angle_canvas)
        layout.addWidget(QtW.QLabel("<b>Max resolution</b>"))
        layout.addWidget(self._max_resolution_canvas)
        layout.addWidget(QtW.QLabel("<b>CTF spectra</b>"))
        layout.addWidget(self._viewer)
        layout.addWidget(self._mic_list)
        self._last_update = -1.0
        self._update_min_interval = 10.0

    def on_job_updated(self, job_dir, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".ctf":
            self._process_update(force_reload=fp.name.startswith("RELION_JOB_"))
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def initialize(self, job_dir):
        """Initialize the viewer with the job directory."""
        self._process_update(force_reload=True)
        self._viewer.auto_fit()

    def _process_update(self, force_reload: bool = False):
        if self._worker is not None:
            self._worker.quit()
        dt = time.time() - self._last_update
        if not force_reload and dt < self._update_min_interval:
            return
        self._worker = self._prep_data_to_plot(self._job_dir)
        self._last_update = time.time()
        self._start_worker()

    def _clear_everything(self, *_):
        self._defocus_canvas.clear()
        self._astigmatism_canvas.clear()
        self._defocus_angle_canvas.clear()
        self._max_resolution_canvas.clear()
        self._viewer.clear()

    @thread_worker
    def _prep_data_to_plot(self, job_dir: _job_dir.JobDirectory):
        if (final_path := job_dir.path.joinpath("micrographs_ctf.star")).exists():
            df = read_star(final_path).get("micrographs").trust_loop().to_polars()
        else:
            it = self._job_dir.glob_in_subdirs("*_PS.txt")
            arrs = []
            for txtpath in it:
                if (arr := read_ctf_output_txt(txtpath)) is not None:
                    arrs.append(arr)
            if arrs == []:
                yield self._clear_everything, None
                return
            arr = np.stack(arrs, axis=0)
            df = pl.DataFrame(
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
        ctf_paths = [
            (f.name, f.as_posix()) for f in self._job_dir.glob_in_subdirs("*_PS.ctf")
        ]
        yield self._mic_list.set_choices, ctf_paths

        self._worker = None

    def _mic_changed(self, row: tuple[str, str]):
        """Handle changes to selected micrograph."""
        mic_path = self._job_dir.resolve_path(row[1])
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


@register_job("relion.ctfrefine.anisomag")
class QCtfRefineAnisoMagViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout
        self._optics_group_list = QMicrographListWidget(["Optics Group", "Index"])
        self._optics_group_list.current_changed.connect(self._process_update)

        self._view_x_obs = Q2DViewWithTitle("Observed Anisotropic Magnification X")
        self._view_y_obs = Q2DViewWithTitle("Observed Anisotropic Magnification Y")
        self._view_x_fit = Q2DViewWithTitle("Fitted Anisotropic Magnification X")
        self._view_y_fit = Q2DViewWithTitle("Fitted Anisotropic Magnification Y")

        layout_obs = QtW.QHBoxLayout()
        layout_obs.setContentsMargins(0, 0, 0, 0)
        layout_obs.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        layout_obs.addWidget(self._view_x_obs)
        layout_obs.addWidget(self._view_y_obs)

        layout_fit = QtW.QHBoxLayout()
        layout_fit.setContentsMargins(0, 0, 0, 0)
        layout_fit.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        layout_fit.addWidget(self._view_x_fit)
        layout_fit.addWidget(self._view_y_fit)

        layout.addWidget(self._optics_group_list)
        layout.addLayout(layout_obs)
        layout.addLayout(layout_fit)

    def initialize(self, job_dir):
        # update optics group list
        star_path = job_dir.path / "particles_ctf_refine.star"
        optics = OpticsModel.validate_block(read_star_block(star_path, "optics"))
        choices = []
        for name, i in zip(optics.optics_group_name, optics.optics_group):
            choices.append((name, str(i)))
        self._optics_group_list.set_choices(choices)

        # update result views
        self._process_update()

    def _process_update(self):
        row = self._optics_group_list.current_row_texts()
        if row is None:
            return
        index = row[1]
        job_dir = self._job_dir

        path_x_obs = job_dir.path / f"mag_disp_x_optics-group_{index}.mrc"
        path_y_obs = job_dir.path / f"mag_disp_y_optics-group_{index}.mrc"
        path_x_fit = job_dir.path / f"mag_disp_x_fit_optics-group_{index}.mrc"
        path_y_fit = job_dir.path / f"mag_disp_y_fit_optics-group_{index}.mrc"

        # load and set images
        self._view_x_obs.set_image_from_path(path_x_obs, quantile=0.99)
        self._view_y_obs.set_image_from_path(path_y_obs, quantile=0.99)
        self._view_x_fit.set_image_from_path(path_x_fit)
        self._view_y_fit.set_image_from_path(path_y_fit)


@register_job("relion.ctfrefine")
class QCtfRefineViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout
        self._mic_list = QMicrographListWidget(["CTF Refine Result", "Full Path"])
        self._mic_list.setColumnHidden(1, True)
        self._mic_list.current_changed.connect(self._update_scatter)
        self._scatter_plot = Q2DSimpleViewer()
        self._scatter_plot.setFixedSize(480, 480)
        self._hist_plot = QPlotCanvas(self)
        self._last_updated_time = -1.0
        self._update_interval = 10.0
        layout.addWidget(QtW.QLabel("<b>Defocus Plot</b>"))
        layout.addWidget(self._mic_list)
        layout.addWidget(self._scatter_plot)
        layout.addWidget(QtW.QLabel("<b>Histogram of All Defocus</b>"))
        layout.addWidget(self._hist_plot)
        self._current_df: pl.DataFrame | None = None

    def initialize(self, job_dir):
        self._process_update(force_reload=True)

    def on_job_updated(self, job_dir, fp):
        if Path(fp).suffix in [".star"]:
            self._process_update()
            _LOGGER.debug("%s Updated", self._job_dir.job_number)

    def _process_update(self, *, force_reload: bool = False):
        if (
            not force_reload
            and time.time() - self._last_updated_time < self._update_interval
        ):
            return
        self._worker = self._read_items()
        self._start_worker()

    @thread_worker
    def _read_items(self):
        choices = []
        star_paths = []
        for star_path in self._job_dir.glob_in_subdirs("*.star"):
            choices.append((star_path.name, f"{star_path.parent}/{star_path.name}"))
            star_paths.append(star_path)
        yield self._mic_list.set_choices, choices
        self._last_updated_time = time.time()

        # update histogram
        dfs = []
        for star_path in star_paths:
            df = read_star(star_path).first().trust_loop().to_polars()
            dfs.append(self._select_df(df))
        self._current_df = pl.concat(dfs, how="vertical")
        yield self._update_histgram, "defocus"

    def _update_histgram(self, name: str):
        defocus = self._current_df[name]
        self._hist_plot.plot_hist(
            defocus,
            xlabel="Defocus (µm)",
            bins=50,
            range=(defocus.min(), defocus.max()),
        )

    def _update_scatter(self):
        row = self._mic_list.current_row_texts()
        if row is None:
            return self._scatter_plot.set_points(np.zeros((0, 2)))
        title, path = row
        star_path = self._job_dir.resolve_path(path)
        df = read_star(star_path).first().trust_loop().to_polars()
        if df.is_empty():
            self._scatter_plot.set_points(np.zeros((0, 2)))
        else:
            df = self._select_df(df)
            xy = df.select("x", "y")
            mic_path = self._job_dir.resolve_path(df["mic_name"][0])
            with mrcfile.open(mic_path, header_only=True) as mrc:
                nx, ny = mrc.header.nx, mrc.header.ny

            color_vals = df["defocus"].to_numpy()
            norm = (color_vals - color_vals.min()) / (
                color_vals.max() - color_vals.min()
            )
            fcolors = get_colormap("viridis").map(norm)
            self._scatter_plot.set_points(
                xy.to_numpy(),
                face_color=fcolors,
                edge_color="#00000000",
            )
            self._scatter_plot.set_border((ny, nx))
        self._scatter_plot.auto_fit()

    def _select_df(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.select(
            x=pl.col("rlnCoordinateX"),
            y=pl.col("rlnCoordinateY"),
            # use um for defocus
            defocus=(pl.col("rlnDefocusU") + pl.col("rlnDefocusV")) / 20000,
            defocus_angle=pl.col("rlnDefocusAngle"),
            bfactor=pl.col("rlnCtfBfactor"),
            scale_factor=pl.col("rlnCtfScalefactor"),
            phase_shift=pl.col("rlnPhaseShift"),
            mic_name=pl.col("rlnMicrographName"),
        )


class Q2DViewWithTitle(QtW.QWidget):
    def __init__(self, title: str):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QtW.QLabel(f"<b>{title}</b>")
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(label)
        self.view = Q2DSimpleViewer()
        self.view.setFixedSize(260, 260)
        layout.addWidget(self.view)

    def set_image_from_path(self, path: Path, quantile: float = 1.0):
        if not path.exists():
            self.view.set_image(None)
        else:
            with mrcfile.open(path, mode="r") as mrc:
                img = np.array(mrc.data)
            if quantile < 1.0:
                lim_positive = np.quantile(np.abs(img), quantile)
                clim = (-lim_positive, lim_positive)
            else:
                clim = None
            self.view.set_image(img, cmap=Colormap(["blue", "black", "red"]), clim=clim)
            self.view.auto_fit()
