from __future__ import annotations
from pathlib import Path
from qtpy import QtWidgets as QtW
from himena_relion._widgets import (
    Q2DViewer,
    Q2DFilterWidget,
    QMicrographListWidget,
)
from himena_relion import _job_dir
from himena_relion._image_readers import ArrayFilteredView


TOMO_VIEW_MIN_HEIGHT = 480
TXT_OR_DIR = [".out", ".err", ".star", ""]


class _QTomogramViewerBase(QtW.QWidget):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = QtW.QVBoxLayout(self)

        self._viewer = Q2DViewer()
        self._viewer.setMinimumHeight(TOMO_VIEW_MIN_HEIGHT)
        self._filter_widget = Q2DFilterWidget()
        self._filter_widget._bin_factor.setText("4")
        self._tomo_list = QMicrographListWidget(["Tomogram", "Type"])
        self._tomo_list.current_changed.connect(self._on_tomo_changed)
        layout.addWidget(QtW.QLabel("<b>Tomogram Z slice</b>"))
        layout.addWidget(self._tomo_list)
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._viewer)
        self._filter_widget.value_changed.connect(self._viewer.redraw)
        self.initialize(job_dir)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        is_new_tomo = fp.parent.name == "tomograms" and fp.suffix == ".mrc"
        if fp.name.startswith("RELION_JOB_") or is_new_tomo:
            self.initialize(job_dir)

    def _get_binned_angpix(self, job_dir: _job_dir.ExternalJobDirectory) -> float:
        return float(job_dir.get_job_param("outbin", "1"))

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        items: list[tuple[str, ...]] = []
        job_dir = self._job_dir

        row_count_old = self._tomo_list.rowCount()
        self._filter_widget.set_image_scale(self._get_binned_angpix(job_dir))
        for p in job_dir.path.joinpath("tomograms").glob("*.mrc"):
            if item := self._prep_item(p):
                items.append(item)
        if len(items) == row_count_old:
            # No need to update. Note that IMOD tilt command updates the mrc file many
            # times during reconstruction.
            return
        items.sort(key=lambda x: x[0])
        self._tomo_list.set_choices(items)
        if len(items) == 0:
            self._viewer.clear()
            self._filter_widget.set_label_text("")
        elif len(items) == 1:
            self._viewer.auto_fit()

    def _on_tomo_changed(self, texts: tuple[str, ...]):
        """Update the viewer when the selected tomogram changes."""
        text = texts[0]
        if tomo_view := self._get_filtered_view(self._job_dir, text):
            tomo_view.try_memmap()
            self._viewer.set_array_view(
                tomo_view.with_filter(self._filter_widget.apply),
                self._viewer._last_clim,
            )
            shape = (tomo_view.num_slices(),) + tomo_view.get_shape()
            scale = tomo_view.get_scale()
            self._filter_widget.set_label_text(f"{shape} {scale:.2f} Å/pix")

    def _get_filtered_view(
        self,
        job_dir: _job_dir.JobDirectory,
        text: str,
    ) -> ArrayFilteredView | None:
        raise NotImplementedError

    def _prep_item(self):
        raise NotImplementedError


class QIMODTomogramViewer(_QTomogramViewerBase):
    def _get_filtered_view(
        self,
        job_dir: _job_dir.JobDirectory,
        text: str,
    ) -> ArrayFilteredView | None:
        mrc_path = job_dir.path / "tomograms" / f"rec_{text}.mrc"
        if mrc_path.exists():
            return ArrayFilteredView.from_mrc(mrc_path)

    def _prep_item(self, p: Path) -> tuple[str, str]:
        return p.stem[4:], "full tomogram"


class QIMODTomogramHalvesViewer(_QTomogramViewerBase):
    def _get_filtered_view(
        self,
        job_dir: _job_dir.JobDirectory,
        text: str,
    ) -> ArrayFilteredView | None:
        mrc_path1 = job_dir.path / "tomograms" / f"rec_{text}_half1.mrc"
        mrc_path2 = job_dir.path / "tomograms" / f"rec_{text}_half2.mrc"
        if mrc_path1.exists() or mrc_path2.exists():
            return ArrayFilteredView.from_mrc_splits([mrc_path1, mrc_path2])
        else:
            return None

    def _prep_item(self, p: Path) -> tuple[str, str] | None:
        if p.stem.endswith("_half2"):
            return
        elif p.stem.endswith("_half1"):
            # strip off "rec_" prefix and "_half1" suffix
            return p.stem[4:-6], "half tomograms"
