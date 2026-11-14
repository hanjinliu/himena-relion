from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import logging
import time
from typing import Callable
from qtpy import QtWidgets as QtW, QtCore
from superqt.utils import thread_worker
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
from himena_relion._widgets._shared.resizer import QResizer
from himena_relion.schemas import TSModel, TSGroupModel

_LOGGER = logging.getLogger(__name__)
TILT_VIEW_MIN_HEIGHT = 480
EXCLUDED_VIEW_MIN_HEIGHT = 420
EXCLUDED_VIEW_MAX_HEIGHT = 480
SELECTED_TILT_SERIES_STAR = "selected_tilt_series.star"
EXCLUDED_TILTS_STAR = "excluded_tilts.star"  # only written by the external job


@dataclass
class CorrectedPaths:
    paths: list[Path]
    total: int


@register_job("relion.motioncorr", is_tomo=True)
class QMotionCorrViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir

        self._viewer = Q2DViewer(zlabel="Tilt index")
        self._viewer.setMinimumHeight(TILT_VIEW_MIN_HEIGHT)
        self._resizer = QResizer(self._viewer)
        self._filter_widget = Q2DFilterWidget(bin_default=8, lowpass_default=30)
        self._ts_list = QMicrographListWidget(["Tilt Series", "Processed"])
        self._ts_list.current_changed.connect(self._ts_choice_changed)
        self._layout.setSpacing(2)
        self._layout.addWidget(
            QtW.QLabel("<b>&#9679; Motion-corrected tilt series</b>")
        )
        self._layout.addWidget(self._ts_list)
        self._layout.addWidget(self._filter_widget)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(self._resizer)
        self._filter_widget.value_changed.connect(self._param_changed)
        self._binsize_old = -1

        self._import_job_tilt_series_star_path: Path | None = None
        self._import_job_ts_models: dict[str, TSModel] = {}
        self._mcor_paths: dict[str, CorrectedPaths] = {}
        self._last_update_time = time.time()
        self._update_min_interval = 5.0

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.suffix == ".star":
            self._process_update(force_update=fp.name.startswith("RELION_JOB_"))
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
        rln_dir = job_dir.relion_project_dir
        mic_star_path = job_dir.get_job_param("input_star_mics")
        self._import_job_tilt_series_star_path = rln_dir / mic_star_path
        self._process_update(force_update=True)
        self._viewer.auto_fit()

    def _process_update(self, force_update: bool = False):
        t0 = time.time()
        if force_update or t0 - self._last_update_time > self._update_min_interval:
            self.window_closed_callback()
            self._worker = self._read_items()
            self._last_update_time = t0
            self._start_worker()

    @thread_worker
    def _read_items(self):
        # cache tilt series models
        if self._import_job_tilt_series_star_path is None:
            return
        if not self._import_job_ts_models:
            _import_job_ts_models = {}
            tomo_meta = TSGroupModel.validate_file(
                self._import_job_tilt_series_star_path
            )
            rln_dir = self._job_dir.relion_project_dir
            for tomo_name, ts_path in zip(
                tomo_meta.tomo_name,
                tomo_meta.tomo_tilt_series_star_file,
            ):
                ts_model = TSModel.validate_file(rln_dir / ts_path)
                _import_job_ts_models[tomo_name] = ts_model
                yield
            self._import_job_ts_models = _import_job_ts_models

        finished_tomo_names: list[str] = []
        new_mcor_paths = self._mcor_paths.copy()
        for tomo_name, ts_model in self._import_job_ts_models.items():
            paths_movies = ts_model.ts_movie_paths_sorted()
            new_paths = []
            for path_mov in paths_movies:
                path_in_mcor = self._job_dir.path / path_mov
                name_mcor = path_in_mcor.stem.replace(".", "_") + ".mrc"
                path_in_mcor = path_in_mcor.parent / name_mcor
                if path_in_mcor.exists():
                    new_paths.append(path_in_mcor)
                yield
            new_mcor_paths[tomo_name] = CorrectedPaths(new_paths, len(paths_movies))
            if len(new_paths) == len(paths_movies) and len(paths_movies) > 0:
                # no longer need to iterate over this tomogram
                finished_tomo_names.append(tomo_name)

        # remove finished tomograms from the cache
        for tomo_name in finished_tomo_names:
            self._import_job_ts_models.pop(tomo_name, None)

        self._mcor_paths = new_mcor_paths

        # setup tilt series list
        choices: list[tuple[str, ...]] = []
        for tomo_name, corrected in self._mcor_paths.items():
            if (num_processed := len(corrected.paths)) > 0:
                choices.append((tomo_name, f"{num_processed}/{corrected.total}"))

        yield self._ts_list.set_choices, choices
        if self._ts_list.current_text() in self._import_job_ts_models:
            # not finished yet, need reload
            self._ts_list._on_selection_changed()
        self._worker = None

    def _ts_choice_changed(self, texts: tuple[str, ...]):
        """Update the viewer when the selected tomogram changes."""
        text = texts[0]
        corrected = self._mcor_paths.get(text, None)
        if corrected is None or len(corrected.paths) == 0:
            self._viewer.clear()
            return
        ts_view = ArrayFilteredView.from_mrcs(corrected.paths)
        self._filter_widget.set_image_scale(ts_view.get_scale())
        self._viewer.set_array_view(ts_view.with_filter(self._filter_widget.apply))
        scale = ts_view.get_scale()
        shape = ts_view.get_shape()
        self._filter_widget.set_label_text(f"{shape} {scale:.2f} Å/pix")


class QExcludeTiltsWidget(QtW.QWidget):
    """Excluded tilt images on top, the remaining tilt series below.

    Shared by the builtin "Exclude Tilts" job and the "Auto Exclude Tilt Images"
    external job. Both jobs write `selected_tilt_series.star`; only the way to list
    the excluded micrographs differs, so it is given as `list_excluded`.
    """

    def __init__(
        self,
        job_dir: _job_dir.JobDirectory,
        list_excluded: Callable[[_job_dir.JobDirectory], list[str]],
    ):
        super().__init__()
        self._job_dir = job_dir
        self._list_excluded = list_excluded

        self._filter_widget = Q2DFilterWidget(bin_default=8, lowpass_default=30)

        self._excluded_list = QMicrographListWidget(["Micrograph"])
        self._excluded_list.current_changed.connect(self._excluded_choice_changed)
        self._excluded_viewer = Q2DViewer()
        self._excluded_viewer.setMinimumHeight(EXCLUDED_VIEW_MIN_HEIGHT)
        self._excluded_viewer.setMaximumHeight(EXCLUDED_VIEW_MAX_HEIGHT)

        self._ts_choice = QMicrographListWidget(["Tilt Series", "Number of Tilts"])
        self._ts_choice.current_changed.connect(self._ts_choice_changed)
        self._viewer = Q2DViewer(zlabel="Tilt index")
        self._viewer.setMinimumHeight(TILT_VIEW_MIN_HEIGHT)
        self._resizer = QResizer(self._viewer)

        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        layout.addWidget(QtW.QLabel("<b>&#9679; Excluded tilts</b>"))
        layout.addWidget(self._excluded_list)
        layout.addWidget(self._excluded_viewer)
        layout.addWidget(QtW.QLabel("<b>&#9679; Selected tilt series</b>"))
        layout.addWidget(self._ts_choice)
        layout.addWidget(self._filter_widget)
        layout.addWidget(self._viewer)
        layout.addWidget(self._resizer)
        # the filter is shared by both viewers
        self._filter_widget.value_changed.connect(self._param_changed)
        self._binsize_old = self._filter_widget.bin_factor()

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        fp = Path(path)
        if fp.name.startswith("RELION_JOB_") or fp.name in (
            SELECTED_TILT_SERIES_STAR,
            EXCLUDED_TILTS_STAR,
        ):
            self._process_update()
            _LOGGER.debug("%s Updated", job_dir.job_number)

    def _param_changed(self):
        """Handle changes to filter parameters."""
        viewers = [self._excluded_viewer, self._viewer]
        for viewer in viewers:
            viewer.redraw()
        new_binsize = self._filter_widget.bin_factor()
        if self._binsize_old != new_binsize:
            self._binsize_old = new_binsize
            for viewer in viewers:
                viewer.auto_fit()

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        self._process_update()
        self._viewer.auto_fit()

    def _process_update(self):
        excluded = self._list_excluded(self._job_dir)
        _set_choices_and_reload(self._excluded_list, [(mic,) for mic in excluded])
        if len(excluded) == 0:
            self._excluded_viewer.clear()

        choices: list[tuple[str, str]] = []
        for p in iter_tilt_series_excludetilt(self._job_dir):
            file = self._job_dir.resolve_path(p.tomo_tilt_series_star_file)
            num_tilts = len(read_star(file).first().trust_loop())
            choices.append((file.stem, str(num_tilts)))

        choices.sort(key=lambda x: x[0])
        _set_choices_and_reload(self._ts_choice, choices)
        if len(choices) == 0:
            self._viewer.clear()

    def _excluded_choice_changed(self, texts: tuple[str]):
        """Update the viewer when the selected excluded micrograph changes."""
        path = self._job_dir.resolve_path(texts[0])
        if not path.exists():
            self._excluded_viewer.clear()
            return
        mic_view = ArrayFilteredView.from_mrc(path)
        self._filter_widget.set_image_scale(mic_view.get_scale())
        self._excluded_viewer.set_array_view(
            mic_view.with_filter(self._filter_widget.apply)
        )

    def _ts_choice_changed(self, texts: tuple[str, str]):
        """Update the viewer when the selected tomogram changes."""
        job_dir = self._job_dir
        text = texts[0]
        for info in iter_tilt_series_excludetilt(job_dir):
            if info.tomo_tilt_series_star_file.stem == text:
                break
        else:
            return
        ts_view = info.read_tilt_series(job_dir.relion_project_dir)
        if ts_view.num_slices() == 0:  # all tilts excluded
            self._viewer.clear()
            self._filter_widget.set_label_text("")
            return
        self._filter_widget.set_image_scale(info.tomo_tilt_series_pixel_size)
        self._viewer.set_array_view(ts_view.with_filter(self._filter_widget.apply))

        scale = ts_view.get_scale()
        shape = ts_view.get_shape()
        self._filter_widget.set_label_text(f"{shape} {scale:.2f} Å/pix")


@register_job("relion.excludetilts", is_tomo=True)
class QExcludeTiltViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._job_dir = job_dir
        self._content = QExcludeTiltsWidget(job_dir, list_excluded_by_comparison)
        self._layout.addWidget(self._content)

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        self._content.on_job_updated(job_dir, path)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        self._content.initialize(job_dir)


def _set_choices_and_reload(
    list_widget: QMicrographListWidget,
    choices: list[tuple[str, ...]],
):
    """Set choices, and reload the selected row since its content may have changed."""
    was_empty = list_widget.rowCount() == 0
    list_widget.set_choices(choices)
    if not was_empty:  # if empty, `set_choices` already selected and emitted row 0
        list_widget._on_selection_changed()


def iter_tilt_series_excludetilt(self: _job_dir.JobDirectory):
    """Iterate over all selected tilt series info."""
    star_path = self.path / SELECTED_TILT_SERIES_STAR
    if not star_path.exists():
        return
    star = read_star(star_path).first().trust_loop().to_polars()
    for row in star.iter_rows(named=True):
        yield _job_dir.SelectedTiltSeriesInfo.from_dict(row)


def list_excluded_by_comparison(job_dir: _job_dir.JobDirectory) -> list[str]:
    """List micrographs that are in the input but not in the selected tilt series.

    The builtin job does not write the excluded tilts, so they are listed by comparing
    the input tilt series (`in_tiltseries`) with `selected_tilt_series.star`. A tilt
    series missing from the output counts as fully excluded.
    """
    if not job_dir.path.joinpath(SELECTED_TILT_SERIES_STAR).exists():
        return []  # not saved yet
    in_path = job_dir.resolve_path(job_dir.get_job_param("in_tiltseries"))
    if not in_path.is_file():
        return []
    kept: dict[str, set[str]] = {}
    for info in iter_tilt_series_excludetilt(job_dir):
        ts_path = job_dir.resolve_path(info.tomo_tilt_series_star_file)
        kept[info.tomo_name] = set(_read_micrograph_names(ts_path))

    df_in = read_star(in_path).first().trust_loop().to_polars()
    excluded: list[str] = []
    for tomo_name, ts_path in zip(
        df_in["rlnTomoName"], df_in["rlnTomoTiltSeriesStarFile"]
    ):
        kept_mics = kept.get(tomo_name, set())
        for mic in _read_micrograph_names(job_dir.resolve_path(ts_path)):
            if mic not in kept_mics:
                excluded.append(mic)
    return excluded


def _read_micrograph_names(ts_star_path: Path) -> list[str]:
    if not ts_star_path.is_file():
        return []
    df = read_star(ts_star_path).first().trust_loop().to_polars()
    if "rlnMicrographName" not in df.columns:
        return []
    return df["rlnMicrographName"].to_list()
