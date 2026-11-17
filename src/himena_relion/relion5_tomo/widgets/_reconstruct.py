from __future__ import annotations
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, NamedTuple
import logging

import mrcfile
import numpy as np
from qtpy import QtWidgets as QtW, QtCore
from superqt.utils import thread_worker
from himena_relion._widgets import (
    QJobScrollArea,
    Q3DViewer,
    register_job,
    QNumParticlesLabel,
    QSymmetryLabel,
    QLowpassParamWidget,
)
from himena_relion._widgets._shared.resizer import QResizer
from himena_relion import _job_dir
from himena_relion._utils import lowpass_filter
from himena_relion.schemas import OptimisationSetModel, TomogramsGroupModel

_LOGGER = logging.getLogger(__name__)
# Reading a reconstruction is retried if it failed, such as when RELION has not finished
# writing the file yet.
_RETRY_INTERVAL_MSEC = 1000
_MAX_RETRY = 5


class _MapData(NamedTuple):
    """A reconstruction read from the job directory."""

    image: np.ndarray
    scale: float  # pixel size in Å
    title: str
    is_final: bool  # True if merged.mrc


@dataclass
class _ReadResult:
    """Output of the worker that reads the reconstruction."""

    load_id: int
    job_dir: _job_dir.JobDirectory
    map_data: _MapData | None = None  # None if no reconstruction is found
    image_filtered: np.ndarray | None = None
    cutoff_a: float = -1.0  # lowpass cutoff used for `image_filtered`
    n_particles: int | None = None  # None if not read
    sym_name: str = ""
    error: Exception | None = None


@register_job("relion.reconstructparticletomo", is_tomo=True)
class QReconstructViewer(QJobScrollArea):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        super().__init__()
        self._file_name_label = QtW.QLabel()
        self._lowpass_widget = QLowpassParamWidget()
        self._lowpass_widget.value_changed.connect(self._on_lowpass_changed)
        self._viewer = Q3DViewer()
        self._viewer.setMaximumWidth(400)
        self._resizer = QResizer(self._viewer)
        self._sym_label = QSymmetryLabel()
        self._sym_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self._num_particles_label = QNumParticlesLabel()
        self._num_particles_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._num_particles_label.setMaximumWidth(self._viewer.maximumWidth())

        self._layout.setSpacing(0)
        self._layout.addWidget(self._file_name_label)
        self._layout.addWidget(self._lowpass_widget)
        self._layout.addWidget(self._viewer)
        self._layout.addWidget(self._resizer)

        hlayout = QtW.QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(self._sym_label)
        hlayout.addWidget(self._num_particles_label)
        self._layout.addLayout(hlayout)

        self._img_raw = None
        self._img_raw_scale = 1.0

        # Reading a reconstruction (and the Wiener filter for intermediate results)
        # runs in a worker thread. Every read has a new ID, so that the values yielded
        # by an outdated worker are ignored.
        self._load_id = 0

        # A file event may come before RELION finishes writing a large file.
        self._num_retry = 0
        self._job_dir_to_retry: _job_dir.JobDirectory | None = None
        self._retry_timer = QtCore.QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.setInterval(_RETRY_INTERVAL_MSEC)
        self._retry_timer.timeout.connect(self._retry_load_result)

        # Loading a reconstruction is expensive. While this widget is hidden (another
        # tab is selected, or the window is minimized), the update is postponed until
        # it is shown.
        self._job_dir_to_update: _job_dir.JobDirectory | None = None

    def on_job_updated(self, job_dir: _job_dir.JobDirectory, path: str):
        """Handle changes to the job directory."""
        self.on_job_files_updated(job_dir, [Path(path)])

    def on_job_files_updated(self, job_dir: _job_dir.JobDirectory, fps: list[Path]):
        if any(_is_result_file(Path(fp)) for fp in fps):
            # the result is read only once for all the files
            if self.isVisible():
                self.initialize(job_dir)
                _LOGGER.debug("%s Updated", job_dir.job_number)
            else:
                self._postpone_update(job_dir)

    def initialize(self, job_dir: _job_dir.JobDirectory):
        """Initialize the viewer with the job directory."""
        self._job_dir_to_update = None
        self._num_retry = 0
        self._load_result(job_dir)

    def showEvent(self, a0):
        super().showEvent(a0)
        if (job_dir := self._job_dir_to_update) is not None:
            try:
                self.initialize(job_dir)
            except Exception:
                _LOGGER.error(
                    "Failed to update the reconstruction of %s.",
                    job_dir.job_number,
                    exc_info=True,
                )

    def window_closed_callback(self):
        self._retry_timer.stop()
        self._job_dir_to_retry = None
        self._job_dir_to_update = None
        self._load_id += 1  # ignore the values already yielded by the worker
        super().window_closed_callback()

    def _postpone_update(self, job_dir: _job_dir.JobDirectory):
        """Load the result when this widget is shown next time."""
        # the update after shown replaces the pending retry
        self._retry_timer.stop()
        self._job_dir_to_retry = None
        self._job_dir_to_update = job_dir
        _LOGGER.debug("%s Update postponed while hidden", job_dir.job_number)

    def _retry_load_result(self):
        if (job_dir := self._job_dir_to_retry) is not None:
            if self.isVisible():
                self._load_result(job_dir)
            else:
                self._postpone_update(job_dir)

    def _load_result(self, job_dir: _job_dir.JobDirectory):
        """Start reading the result in a worker thread."""
        # this attempt replaces the pending retry and the running worker
        self._retry_timer.stop()
        self._job_dir_to_retry = None
        self._stop_worker()
        self._load_id += 1
        self._worker = self._read_result(
            job_dir,
            load_id=self._load_id,
            cutoff_a=self._lowpass_widget.value(),
            read_n_particles=not self._num_particles_label.num_known(),
        )
        self._start_worker()

    @thread_worker
    def _read_result(
        self,
        job_dir: _job_dir.JobDirectory,
        load_id: int,
        cutoff_a: float,
        read_n_particles: bool,
    ):
        """Read the reconstruction. This runs in a worker thread.

        Widgets must not be touched here. The result is passed to the main thread by
        yielding `_on_read_finished`. Bare `yield`s between the heavy steps allow the
        worker to stop as soon as possible after `quit()`.
        """
        result = _ReadResult(load_id, job_dir)
        try:
            merged_mrc_path = job_dir.path / "merged.mrc"
            if merged_mrc_path.exists():
                map_data = _read_final_result(merged_mrc_path)
            else:
                map_data = yield from _iter_read_intermediate_result(job_dir)
            if map_data is not None:
                yield
                result.image_filtered = _filter_image(
                    map_data.image, map_data.scale, cutoff_a
                )
                result.cutoff_a = cutoff_a
                yield
                if read_n_particles:
                    n_particles = _job_dir.try_get_particle_number(job_dir)
                    result.n_particles = n_particles if n_particles is not None else -1
                result.sym_name = job_dir.get_job_param("sym_name")
            result.map_data = map_data
        except Exception as e:
            result.error = e
        yield self._on_read_finished, result

    def _on_read_finished(self, result: _ReadResult):
        """Update the widgets with the result read in the worker thread."""
        if result.load_id != self._load_id:
            return  # outdated
        self._worker = None
        if result.error is not None:
            self._on_read_failed(result.job_dir, result.error)
            return
        self._num_retry = 0

        if (map_data := result.map_data) is None:
            self._clear_image()
            return

        self._img_raw = map_data.image
        self._img_raw_scale = map_data.scale
        if result.cutoff_a == self._lowpass_widget.value():
            img_filtered = result.image_filtered
        else:
            # the lowpass parameter was changed while reading
            img_filtered = self._get_image_filtered()
        self._file_name_label.setText(map_data.title)
        if map_data.is_final:
            self._viewer.set_image(img_filtered, update_now=False)
            self._viewer.auto_threshold(update_now=False)
            self._viewer.auto_fit()
        else:
            was_empty = not self._viewer.has_image
            self._viewer.set_image(img_filtered, update_now=was_empty)
            if was_empty:
                self._viewer.auto_threshold(update_now=False)
                self._viewer.auto_fit()

        if result.n_particles is not None and not self._num_particles_label.num_known():
            self._num_particles_label.set_number(result.n_particles)
        self._sym_label.set_symmetry(result.sym_name)

    def _on_read_failed(self, job_dir: _job_dir.JobDirectory, error: Exception):
        if self._num_retry < _MAX_RETRY:
            self._num_retry += 1
            _LOGGER.debug(
                "Failed to read the reconstruction of %s. Retry in %d ms (%d/%d).",
                job_dir.job_number,
                _RETRY_INTERVAL_MSEC,
                self._num_retry,
                _MAX_RETRY,
                exc_info=error,
            )
            self._job_dir_to_retry = job_dir
            self._retry_timer.start()
        else:
            _LOGGER.warning(
                "Failed to read the reconstruction of %s.",
                job_dir.job_number,
                exc_info=error,
            )

    def _on_lowpass_changed(self):
        self._viewer.set_image(self._get_image_filtered(), update_now=True)

    def _clear_image(self):
        self._img_raw = None
        self._viewer.set_image(None, update_now=False)

    def _get_image_filtered(self):
        if (img := self._img_raw) is None:
            return None
        return _filter_image(img, self._img_raw_scale, self._lowpass_widget.value())


def _is_result_file(fp: Path) -> bool:
    """True if the file update means that the reconstruction may have changed."""
    # NOTE: sometimes half1 will not be generated.
    return (
        fp.name.startswith("RELION_JOB_")
        or fp.name == "merged.mrc"
        or fp.name.endswith("_data_half0.mrc")
    )


def _filter_image(img: np.ndarray, scale: float, cutoff_a: float) -> np.ndarray:
    """Apply the lowpass filter of `cutoff_a` Å (not applied if negative)."""
    return lowpass_filter(img, scale / cutoff_a)


def _read_final_result(merged_mrc_path: Path) -> _MapData:
    with mrcfile.open(merged_mrc_path) as mrc:
        img_raw = np.array(mrc.data)
        img_raw_scale = float(mrc.voxel_size.x)
    return _MapData(img_raw, img_raw_scale, merged_mrc_path.name, is_final=True)


def _iter_read_intermediate_result(
    job_dir: _job_dir.JobDirectory,
) -> Generator[None, None, _MapData | None]:
    """Read the intermediate result, yielding between the heavy steps.

    Return None if no intermediate result is found.
    """
    temp_dir = job_dir.path / "temp"
    if not temp_dir.exists():
        return None
    image_data: list[np.ndarray] = []
    ctf_data: list[np.ndarray] = []
    ith_tomo = "0"
    # MPI = 1: sum_1_data_half?.mrc
    # MPI > 1: sum_rank_0_1_data_half?.mrc
    for impath in temp_dir.glob("sum_*_data_half?.mrc"):
        with suppress(FileNotFoundError):
            with mrcfile.open(impath, mode="r") as mrc:
                image_data.append(mrc.data)
            ith_tomo = impath.stem.split("_data_half")[0].split("_")[-1]
        yield
    for ctfpath in temp_dir.glob("sum_*_ctf_half?.mrc"):
        with suppress(FileNotFoundError), mrcfile.open(ctfpath, mode="r") as mrc:
            ctf_data.append(mrc.data)
        yield
    if len(image_data) == 0:
        return None
    # Every sum_X_data_halfX.mrc is a (2N, N, N/2) float32 image for a (N, N, N)
    # reconstruction. The first N planes are the real part and the next N planes are
    # the imaginary part of the Fourier transform.
    merged_c = sum(image_data)
    nz = merged_c.shape[0]
    merged_ft = merged_c[: nz // 2] + merged_c[nz // 2 :] * 1j

    # Every sum_X_ctf_halfX.mrc is a (N, N, N/2) float32 image containing the CTF.
    if ctf_data and len(image_data) >= 2:
        ctf_c = sum(ctf_data)
        # Wiener filter deconvolution
        # Estimate noise power from image_data half set
        diff = image_data[0] - image_data[1]
        noise_power = np.var(diff) / 4
        wiener_filter = np.conj(ctf_c) / (np.abs(ctf_c) ** 2 + noise_power)
        merged_ft = merged_ft * wiener_filter
        yield

    img_raw = np.fft.ifftshift(np.fft.irfftn(merged_ft))
    yield

    # Try to get the pixel size. Pixel size is not set in the sum_X_data_halfX.mrc
    # files, so we need to retrieve it from the input parameters.
    params = job_dir.get_job_params_as_dict()

    tomo_star = None
    binning = 1
    with suppress(Exception):
        binning = int(params["binning"])
        if in_opt := params["in_optimisation"]:
            tomo_star = OptimisationSetModel.validate_file(
                job_dir.resolve_path(in_opt)
            ).tomogram_star
        elif in_tomo := params["in_tomograms"]:
            tomo_star = job_dir.resolve_path(in_tomo)

    if tomo_star:
        tomo_model = TomogramsGroupModel.validate_file(tomo_star)
        img_raw_scale = float(tomo_model.original_pixel_size.mean()) * binning
    else:
        img_raw_scale = 0.3 * binning  # fallback

    title = f"Intermediate reconstruction ({int(ith_tomo) + 1})"
    return _MapData(img_raw, img_raw_scale, title, is_final=False)
