from __future__ import annotations
from pathlib import Path
import logging
from qtpy import QtWidgets as QtW
from starfile_rs import read_star
from himena_relion._image_readers._array import ArrayFilteredView
from himena_relion._widgets import (
    QJobScrollArea,
    Q2DViewer,
    Q2DFilterWidget,
    register_job,
    QMicrographListWidget,
)
from himena_relion import _job_dir
from himena_relion.schemas import TSModel

_LOGGER = logging.getLogger(__name__)
TILT_VIEW_MIN_HEIGHT = 480


@register_job("relion.motioncorr", is_tomo=True)
class QMotionCorrViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._viewer = Q2DViewer(zlabel="Tilt index")
        self._viewer.setMinimumHeight(TILT_VIEW_MIN_HEIGHT)
        self._filter_widget = Q2DFilterWidget()
        self._ts_list = QMicrographListWidget(["Tilt Series"])
        self._ts_list.current_changed.connect(self._ts_choice_changed)
        layout.addWidget(QtW.QLabel("<b>Motion-corrected tilt series</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._ts_list)
        layout.addWidget(self._viewer)
        self._filter_widget.value_changed.connect(self._param_changed)
        self._binsize_old = -1

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".star":
            self._process_update()
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def _param_changed(self):
        """Handle changes to filter parameters."""
        self._viewer.redraw()
        new_binsize = self._filter_widget.bin_factor()
        if self._binsize_old != new_binsize:
            self._binsize_old = new_binsize
            self._viewer.auto_fit()

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir = job_dir

        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        ts_dir = self._job_dir.path / "tilt_series"
        choices = []
        for p in ts_dir.glob("*.star"):
            choices.append((p.stem,))
        choices.sort(key=lambda x: x[0])
        self._ts_list.set_choices(choices)
        if len(choices) == 0:
            self._viewer.clear()

    def _ts_choice_changed(self, texts: tuple[str, ...]):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        text = texts[0]
        ts_xx_star_path = job_dir.path / "tilt_series" / f"{text}.star"
        if not ts_xx_star_path.exists():
            return

        ts_view = ArrayFilteredView.from_mrcs(
            TSModel.validate_file(ts_xx_star_path).ts_paths_sorted(
                job_dir.relion_project_dir
            )
        )
        self._filter_widget.set_image_scale(ts_view.get_scale())
        self._viewer.set_array_view(ts_view.with_filter(self._filter_widget.apply))


@register_job("relion.excludetilts", is_tomo=True)
class QExcludeTiltViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        layout = self._layout

        self._viewer = Q2DViewer(zlabel="Tilt index")
        self._viewer.setMinimumHeight(TILT_VIEW_MIN_HEIGHT)
        self._filter_widget = Q2DFilterWidget()
        self._ts_choice = QMicrographListWidget(["Tilt Series", "Number of Tilts"])
        self._ts_choice.current_changed.connect(self._ts_choice_changed)
        layout.addWidget(QtW.QLabel("<b>Selected tilt series</b>"))
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._ts_choice)
        layout.addWidget(self._viewer)
        self._filter_widget.value_changed.connect(self._viewer.redraw)
        self._binsize_old = -1

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.name == "selected_tilt_series.star":
            self._process_update()
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def _param_changed(self):
        """Handle changes to filter parameters."""
        self._viewer.redraw()
        new_binsize = self._filter_widget.bin_factor()
        if self._binsize_old != new_binsize:
            self._binsize_old = new_binsize
            self._viewer.auto_fit()

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        choices: list[tuple[str, str]] = []
        for p in iter_tilt_series_excludetilt(self._job_dir):
            file = self._job_dir.resolve_path(p.tomo_tilt_series_star_file)
            num_tilts = len(read_star(file).first().trust_loop())
            choices.append((file.stem, str(num_tilts)))

        choices.sort(key=lambda x: x[0])
        self._ts_choice.set_choices(choices)
        if len(choices) == 0:
            self._viewer.clear()

    def _ts_choice_changed(self, texts: tuple[str, str]):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        text = texts[0]
        for info in iter_tilt_series_excludetilt(job_dir):
            if info.tomo_tilt_series_star_file.stem == text:
                break
        else:
            return
        self._filter_widget.set_image_scale(info.tomo_tilt_series_pixel_size)
        ts_view = info.read_tilt_series(job_dir.relion_project_dir)
        self._viewer.set_array_view(ts_view.with_filter(self._filter_widget.apply))


def iter_tilt_series_excludetilt(self: _job_dir.JobDirectory):
    """Iterate over all excluded tilt series info."""
    star_path = self.path / "selected_tilt_series.star"
    if not star_path.exists():
        return
    star = read_star(star_path).first().trust_loop().to_pandas()
    for _, row in star.iterrows():
        yield _job_dir.SelectedTiltSeriesInfo.from_series(row)
