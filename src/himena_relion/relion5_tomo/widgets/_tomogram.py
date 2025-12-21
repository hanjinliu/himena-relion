from __future__ import annotations
from contextlib import suppress
from pathlib import Path
import logging
import numpy as np
import pandas as pd
from qtpy import QtWidgets as QtW
from superqt.utils import thread_worker
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    Q2DFilterWidget,
    register_job,
)
from himena_relion import _job_dir
from himena_relion._image_readers import ArrayFilteredView

_LOGGER = logging.getLogger(__name__)


@register_job(_job_dir.TomogramJobDirectory)
class QTomogramViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job_dir.TomogramJobDirectory = None
        layout = self._layout

        self._viewer = Q2DViewer()
        self._filter_widget = Q2DFilterWidget()
        self._filter_widget._bin_factor.setText("1")
        self._tomo_choice = QtW.QComboBox()
        self._tomo_choice.currentTextChanged.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Tomogram Z slice</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._tomo_choice)
        layout.addWidget(self._viewer)
        self._filter_widget.value_changed.connect(self._viewer.redraw)
        self._is_split = False

    def on_job_updated(self, job_dir: _job_dir.TomogramJobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".mrc":
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_id)

    def initialize(self, job_dir: _job_dir.TomogramJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        current_text = self._tomo_choice.currentText()
        items: list[str] = []
        self._is_split = job_dir.get_job_param("generate_split_tomograms") == "Yes"
        self._filter_widget.set_image_scale(
            float(job_dir.get_job_param("binned_angpix"))
        )
        for p in job_dir.path.joinpath("tomograms").glob("*.mrc"):
            if self._is_split:
                if p.stem.endswith("_half2"):
                    continue
                elif p.stem.endswith("_half1"):
                    items.append(p.stem[4:-6])
            else:
                items.append(p.stem[4:])
        self._tomo_choice.clear()
        self._tomo_choice.addItems(items)
        if len(items) == 0:
            self._viewer.clear()
            self._viewer.redraw()
        if current_text in items:
            self._tomo_choice.setCurrentText(current_text)
        self._on_tomo_changed(self._tomo_choice.currentText())
        self._viewer.auto_fit()

    def _on_tomo_changed(self, text: str):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        if job_dir is None:
            return

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


@register_job(_job_dir.DenoiseJobDirectory)
class QDenoiseTomogramViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job_dir.DenoiseJobDirectory = None
        layout = self._layout

        self._viewer = Q2DViewer()
        self._tomo_choice = QtW.QComboBox()
        self._tomo_choice.currentTextChanged.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Denoised tomogram Z slice</b>"))
        layout.addWidget(self._tomo_choice)
        layout.addWidget(self._viewer)

    def on_job_updated(self, job_dir: _job_dir.DenoiseJobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix not in [
            ".out",
            ".err",
            ".star",
            "",
        ]:
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_id)

    def initialize(self, job_dir: _job_dir.DenoiseJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        if job_dir._is_train:
            return
        current_text = self._tomo_choice.currentText()
        items = [p.stem[4:] for p in job_dir.path.joinpath("tomograms").glob("*.mrc")]
        self._tomo_choice.clear()
        self._tomo_choice.addItems(items)
        if len(items) == 0:
            self._viewer.clear()
            self._viewer.redraw()
        if current_text in items:
            self._tomo_choice.setCurrentText(current_text)
        self._on_tomo_changed(self._tomo_choice.currentText())
        self._viewer.auto_fit()

    def _on_tomo_changed(self, text: str):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        if job_dir is None:
            return
        mrc_path = job_dir.path / "tomograms" / f"rec_{text}.mrc"
        if mrc_path.exists():
            tomo_view = ArrayFilteredView.from_mrc(mrc_path)
            self._viewer.set_array_view(tomo_view, self._viewer._last_clim)


@register_job(_job_dir.PickJobDirectory)
class PickViewer(QJobScrollArea):
    def __init__(self):
        super().__init__()
        self._job_dir: _job_dir.PickJobDirectory = None
        layout = self._layout

        self._viewer = Q2DViewer()
        self._worker = None
        self._current_info: _job_dir.TomogramInfo | None = None
        self._filter_widget = Q2DFilterWidget()
        self._filter_widget._bin_factor.setText("1")
        self._tomo_choice = QtW.QComboBox()
        self._tomo_choice.currentTextChanged.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Picked tomogram Z slice</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._tomo_choice)
        layout.addWidget(self._viewer)
        self._filter_widget.value_changed.connect(self._viewer.redraw)

    def on_job_updated(self, job_dir: _job_dir.PickJobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix not in [
            ".out",
            ".err",
            ".star",
            "",
        ]:
            self.initialize(job_dir)
            _LOGGER.debug("%s Updated", job_dir.job_id)

    def initialize(self, job_dir: _job_dir.PickJobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir
        current_text = self._tomo_choice.currentText()
        items = [info.tomo_name for info in job_dir.iter_tomogram()]
        self._tomo_choice.clear()
        self._tomo_choice.addItems(items)
        if len(items) == 0:
            self._viewer.clear()
            self._viewer.redraw()
        if current_text in items:
            self._tomo_choice.setCurrentText(current_text)
        self._on_tomo_changed(self._tomo_choice.currentText())
        self._viewer.auto_fit()

    def _on_tomo_changed(self, text: str):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        if job_dir is None:
            return
        for info in job_dir.iter_tomogram():
            if info.tomo_name == text:
                break
        else:
            return
        if self._worker is not None and self._worker.is_running:
            self._worker.quit()
            self._worker = None
        tomo_view = info.read_tomogram(job_dir.relion_project_dir)
        self._viewer.set_points(
            np.empty((0, 3), dtype=np.float32)
        )  # first clear points
        self._viewer.set_array_view(tomo_view, self._viewer._last_clim)
        if getter := info.get_particles:
            self._current_info = info
            worker = thread_worker(getter)()
            self._worker = worker
            worker.returned.connect(self._on_worker_returned)
            worker.start()

    def _on_worker_returned(self, point_df: pd.DataFrame):
        self._worker = None
        with suppress(RuntimeError):
            info = self._current_info
            if info is None:
                return
            cols = [f"rlnCenteredCoordinate{x}Angst" for x in "ZYX"]
            points = point_df[cols].to_numpy(dtype=np.float32) / info.tomo_pixel_size
            sizes = np.array(info.tomo_shape, dtype=np.float32) / info.tomogram_binning
            center = (sizes - 1) / 2
            self._viewer.set_points(points + center[np.newaxis])
            self._viewer.redraw()
