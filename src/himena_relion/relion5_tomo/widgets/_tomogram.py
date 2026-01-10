from __future__ import annotations
from pathlib import Path
import logging
import numpy as np
from qtpy import QtWidgets as QtW
from starfile_rs import read_star
from superqt.utils import thread_worker
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    Q2DFilterWidget,
    register_job,
    QMicrographListWidget,
)
from himena_relion import _job_dir
from himena_relion._image_readers import ArrayFilteredView

_LOGGER = logging.getLogger(__name__)

TOMO_VIEW_MIN_HEIGHT = 480
TXT_OR_DIR = [".out", ".err", ".star", ""]


@register_job("relion.reconstructtomograms", is_tomo=True)
class QTomogramViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.TomogramJobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._viewer = Q2DViewer()
        self._viewer.setMinimumHeight(TOMO_VIEW_MIN_HEIGHT)
        self._filter_widget = Q2DFilterWidget()
        self._filter_widget._bin_factor.setText("1")
        self._tomo_list = QMicrographListWidget(["Tomogram", "Type"])
        self._tomo_list.current_changed.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Tomogram Z slice</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._tomo_list)
        layout.addWidget(self._viewer)
        self._filter_widget.value_changed.connect(self._viewer.redraw)
        self._is_split = False

    def on_job_updated(self, job_dir: _job_dir.TomogramJobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.TomogramJobDirectory):
        """Initialize the viewer with the job directory."""
        items: list[tuple[str, ...]] = []
        job_dir = self._job_dir
        self._is_split = job_dir.get_job_param("generate_split_tomograms") == "Yes"
        self._filter_widget.set_image_scale(
            float(job_dir.get_job_param("binned_angpix"))
        )
        for p in job_dir.path.joinpath("tomograms").glob("*.mrc"):
            if self._is_split:
                if p.stem.endswith("_half2"):
                    continue
                elif p.stem.endswith("_half1"):
                    items.append((p.stem[4:-6], "half tomograms"))
            else:
                items.append((p.stem[4:], "full tomogram"))
        items.sort(key=lambda x: x[0])
        self._tomo_list.set_choices(items)
        if len(items) == 0:
            self._viewer.clear()
        self._viewer.auto_fit()

    def _on_tomo_changed(self, texts: tuple[str, ...]):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        text = texts[0]
        if self._is_split:
            mrc_path1 = job_dir.path / "tomograms" / f"rec_{text}_half1.mrc"
            mrc_path2 = job_dir.path / "tomograms" / f"rec_{text}_half2.mrc"
            tomo_view = ArrayFilteredView.from_mrc_splits([mrc_path1, mrc_path2])
            ok = mrc_path1.exists() or mrc_path2.exists()
        else:
            mrc_path = job_dir.path / "tomograms" / f"rec_{text}.mrc"
            tomo_view = ArrayFilteredView.from_mrc(mrc_path)
            ok = mrc_path.exists()
        if ok:
            self._viewer.set_array_view(
                tomo_view.with_filter(self._filter_widget.apply),
                self._viewer._last_clim,
            )


@register_job("relion.denoisetomo", is_tomo=True)
class QDenoiseTomogramViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.DenoiseJobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._viewer = Q2DViewer()
        self._viewer.setMinimumHeight(TOMO_VIEW_MIN_HEIGHT)
        self._tomo_list = QMicrographListWidget(["Tomogram", "Type"])
        self._tomo_list.current_changed.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Denoised tomogram Z slice</b>"))
        layout.addWidget(self._tomo_list)
        layout.addWidget(self._viewer)

    def on_job_updated(self, job_dir: _job_dir.DenoiseJobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix not in TXT_OR_DIR:
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.DenoiseJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        if job_dir._is_train:
            return
        items = [
            (p.stem[4:], "Denoised")
            for p in job_dir.path.joinpath("tomograms").glob("*.mrc")
        ]
        items.sort(key=lambda x: x[0])
        self._tomo_list.set_choices(items)
        if len(items) == 0:
            self._viewer.clear()

    def _on_tomo_changed(self, texts: tuple[str, ...]):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        text = texts[0]
        mrc_path = job_dir.path / "tomograms" / f"rec_{text}.mrc"
        if mrc_path.exists():
            tomo_view = ArrayFilteredView.from_mrc(mrc_path)
            self._viewer.set_array_view(tomo_view, self._viewer._last_clim)
        else:
            _LOGGER.info("Denoised tomogram file not found: %s", mrc_path)


@register_job("relion.picktomo", is_tomo=True)
class QPickViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.PickJobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._viewer = Q2DViewer()
        self._viewer.setMinimumHeight(TOMO_VIEW_MIN_HEIGHT)
        self._worker = None
        self._current_info: _job_dir.TomogramInfo | None = None
        self._filter_widget = Q2DFilterWidget()
        self._filter_widget._bin_factor.setText("1")
        self._tomo_list = QMicrographListWidget(["Tomogram", "Annotations"])
        self._tomo_list.current_changed.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Picked tomogram Z slice</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._tomo_list)
        layout.addWidget(self._viewer)
        self._filter_widget.value_changed.connect(self._viewer.redraw)

        # Add resize grip in the corner
        self._size_grip = QtW.QSizeGrip(self)
        grip_layout = QtW.QHBoxLayout()
        grip_layout.addStretch()
        grip_layout.addWidget(self._size_grip)
        layout.addLayout(grip_layout)

    def on_job_updated(self, job_dir: _job_dir.PickJobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix not in TXT_OR_DIR:
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def initialize(self, job_dir: _job_dir.PickJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        annot_dir = job_dir.path / "annotations"
        items = []
        for info in job_dir.iter_tomogram():
            tomo_name = info.tomo_name
            annot_files = list(annot_dir.glob(f"{tomo_name}_*.star"))
            if annot_files:
                annot_path = annot_files[0]
                units = annot_path.stem[len(tomo_name) + 1 :]
                loop = read_star(annot_path).first().trust_loop()
                if units == "filaments":
                    # filament vertices are labeled with rlnTomoManifoldIndex
                    n_annot = loop.to_pandas()["rlnTomoManifoldIndex"].nunique()
                else:
                    n_annot = len(loop)
                items.append((info.tomo_name, f"{n_annot} {units}"))
            else:
                items.append((info.tomo_name, "0"))
        self._tomo_list.set_choices(items)
        if len(items) == 0:
            self._viewer.clear()

    def _on_tomo_changed(self, texts: tuple[str, ...]):
        """Update the viewer when the selected tomogram changes."""
        self.window_closed_callback()
        self._worker = self._read_items(texts[0])
        self._start_worker()

    @thread_worker
    def _read_items(self, text: str):
        # first clear points
        yield self._viewer.set_points, np.empty((0, 3), dtype=np.float32)
        for info in self._job_dir.iter_tomogram():
            if info.tomo_name == text:
                break
        else:
            return
        tomo_view = info.read_tomogram(self._job_dir.relion_project_dir)
        self._filter_widget.set_image_scale(info.tomo_pixel_size)
        yield self._set_tomo_view, tomo_view.with_filter(self._filter_widget.apply)
        if getter := info.get_particles:
            point_df = getter()
            cols = [f"rlnCenteredCoordinate{x}Angst" for x in "ZYX"]
            points = point_df[cols].to_numpy(dtype=np.float32) / info.tomo_pixel_size
            sizes = np.array(info.tomo_shape, dtype=np.float32) / info.tomogram_binning
            center = (sizes - 1) / 2
            bin_factor = int(self._filter_widget._bin_factor.text() or "1")
            points_processed = (points + center[np.newaxis]) / bin_factor
            yield self._set_points_and_redraw, points_processed
        self._worker = None

    def _set_tomo_view(self, tomo_view: ArrayFilteredView):
        self._viewer.set_array_view(tomo_view, self._viewer._last_clim)
        self._viewer.redraw()

    def _set_points_and_redraw(self, points: np.ndarray):
        self._viewer.set_points(points)
        self._viewer.redraw()
