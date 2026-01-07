from __future__ import annotations
from pathlib import Path
import logging
import sys
import time
from qtpy import QtGui
from typing import Annotated, Any, get_args, get_origin, TYPE_CHECKING

import numpy as np
from functools import lru_cache

from starfile_rs import read_star
from himena.types import is_subtype
from himena.consts import MonospaceFontFamily
from himena_relion.consts import Type
from himena_relion.schemas import RelionPipelineModel, ParticleMetaModel

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from himena import MainWindow

_LOGGER = logging.getLogger(__name__)


def bin_image(img: np.ndarray, nbin: int) -> np.ndarray:
    """Bin a 2D or 3D image by an integer factor."""
    if img.ndim == 2:
        ny, nx = img.shape
        nyb = ny // nbin
        nxb = nx // nbin
        img = img[: nyb * nbin, : nxb * nbin]
        return img.reshape(nyb, nbin, nxb, nbin).mean(axis=(1, 3))
    elif img.ndim == 3:
        nz, ny, nx = img.shape
        nzb = nz // nbin
        nyb = ny // nbin
        nxb = nx // nbin
        img = img[: nzb * nbin, : nyb * nbin, : nxb * nbin]
        return img.reshape(nzb, nbin, nyb, nbin, nxb, nbin).mean(axis=(1, 3, 5))
    else:
        raise ValueError(f"Expected 2D or 3D image, got {img.ndim}D")


def lowpass_filter(img: np.ndarray, cutoff: float) -> np.ndarray:
    """Apply a low-pass filter to a 2D image in Fourier space."""
    fr = frequency_mesh(img.shape)
    filter_mask = fr <= cutoff
    img_ft = np.fft.fft2(img)
    img_ft_filtered = img_ft * filter_mask
    img_filtered = np.fft.ifft2(img_ft_filtered).real
    return img_filtered


@lru_cache(maxsize=32)
def frequency_mesh(shape: tuple[int, int]) -> np.ndarray:
    """Generate a frequency mesh for a given image shape."""
    fy, fx = np.fft.fftfreq(shape[0]), np.fft.fftfreq(shape[1])
    fxx, fyy = np.meshgrid(fx, fy)
    fr = np.sqrt(fxx**2 + fyy**2)
    return fr


# Adapted from skimage.filters.thresholding (BSD-2-Clause license)
def threshold_yen(image: np.ndarray, nbins=256, use_positive: bool = True) -> float:
    if use_positive:
        input_arr = image[image > 0].ravel()
    else:
        input_arr = image.ravel()
    counts, edges = np.histogram(input_arr, nbins, density=False)
    bin_centers = (edges[:-1] + edges[1:]) / 2

    # On blank images (e.g. filled with 0) with int dtype, `histogram()`
    # returns ``bin_centers`` containing only one value. Speed up with it.
    if bin_centers.size == 1:
        return bin_centers[0]

    # Calculate probability mass function
    pmf = counts.astype("float32", copy=False) / counts.sum()
    P1 = np.cumsum(pmf)  # Cumulative normalized histogram
    P1_sq = np.cumsum(pmf**2)
    # Get cumsum calculated from end of squared array:
    P2_sq = np.cumsum(pmf[::-1] ** 2)[::-1]
    # P2_sq indexes is shifted +1. I assume, with P1[:-1] it's help avoid
    # '-inf' in crit. ImageJ Yen implementation replaces those values by zero.
    crit = np.log(((P1_sq[:-1] * P2_sq[1:]) ** -1) * (P1[:-1] * (1.0 - P1[:-1])) ** 2)
    return float(bin_centers[crit.argmax()])


def path_icon_svg(name: str) -> Path:
    return Path(__file__).parent / "resources" / f"{name}.svg"


def read_icon_svg(name: str) -> str:
    return path_icon_svg(name).read_text(encoding="utf-8")


def read_icon_svg_for_type(type_label: str) -> str:
    match type_label:
        case "DensityMap":
            return read_icon_svg("density")
        case "Mask3D":
            return read_icon_svg("mask")
        case "TomoOptimisationSet":
            return read_icon_svg("optimisation_set")
        case "TomogramGroupMetadata":
            return read_icon_svg("tomograms")
        case "ParticleGroupMetadata":
            return read_icon_svg("particles")
        case "ParticlesData":
            return read_icon_svg("particles")
        case "MicrographMoviesData":
            return read_icon_svg("movies")
        case "MicrographMovieGroupMetadata":
            return read_icon_svg("movies")
        case "MicrographsData" | "MicrographGroupMetadata":
            return read_icon_svg("micrographs")
        case "MicrographsCoords":  # TODO: different icon?
            return read_icon_svg("particles")
        case "Image2DGroupMetadata":  # TODO: make svg
            return read_icon_svg("file")
        case "OptimiserData":
            return read_icon_svg("optimiser")
        case "ProcessData":
            return read_icon_svg("process")
        case "TomoTrajectoryData":
            return read_icon_svg("trajectories")
        case _:
            return read_icon_svg("file")


def make_tilt_projection_mat(deg: float) -> NDArray[np.float32]:
    rad = np.deg2rad(deg)
    cos = np.cos(rad)
    sin = np.sin(rad)
    return np.array([[cos, 0, -sin], [0, 1, 0], [sin, 0, cos]], dtype=np.float32)


def last_job_directory() -> str:
    """Get the identifier of the latest job."""
    pipeline = RelionPipelineModel.validate_file("default_pipeline.star")
    return pipeline.processes.process_name.iloc[-1]


def unwrap_annotated(annot: Any) -> Any:
    """Recursively unwrap Annotated types to get the base type.

    For example, Annotated[str, {...}] -> str.
    """
    origin = get_origin(annot)
    if origin is Annotated:
        args = get_args(annot)
        base_type = args[0]
        return unwrap_annotated(base_type)
    else:
        return annot


def change_name_for_tomo(type_label: str) -> str:
    _relion, _jobname, *_others = type_label.split(".")
    if not _jobname.endswith("tomo"):
        if _others:
            _others = ".".join(_others)
            type_label = f"{_relion}.{_jobname}_tomo.{_others}"
        else:
            type_label = f"{_relion}.{_jobname}_tomo"
    return type_label


def normalize_job_id(d: str | Path) -> str:
    if isinstance(d, Path):
        d = d.as_posix()
    if not d.endswith("/"):
        d += "/"
    if d.count("/") > 2:
        # the last character is "/"
        d = "/".join(d.split("/")[-3:])
    return d


def update_default_pipeline(
    default_pipeline_path: Path,
    job_id: str,
    state: str | None = None,
    alias: str | None = None,
):
    with default_pipeline_path.open("r+") as f:  # use open to acquire lock
        try:
            pipeline_star = RelionPipelineModel.validate_text(f.read())
            pos_sl = pipeline_star.processes.process_name == normalize_job_id(job_id)
            if len(true_ids := np.where(pos_sl)) == 1:
                df = pipeline_star.processes.dataframe
                if state is not None:
                    df.loc[true_ids[0][0], "rlnPipeLineProcessStatusLabel"] = state
                if alias is not None:
                    df.loc[true_ids[0][0], "rlnPipeLineProcessAlias"] = alias
                pipeline_star.processes = df
                f.seek(0)
                f.write(pipeline_star.to_string())
        except Exception:
            _LOGGER.warning("Failed to update job state for %s", job_id, exc_info=True)
    default_pipeline_path.touch()  # update modification time


def read_or_show_job(ui: MainWindow, path: Path):
    """Open a RELION job file in the UI, or switch to it if already opened."""
    from himena_relion._job_dir import JobDirectory

    # if already opened, switch to it
    for i_tab, tab in ui.tabs.enumerate():
        for i_window, window in tab.enumerate():
            if not is_subtype(window.model_type(), Type.RELION_JOB):
                continue
            try:
                val = window.value
                if isinstance(val, JobDirectory) and path == val.path:
                    ui.tabs.current_index = i_tab
                    tab.current_index = i_window
                    return
            except Exception:
                continue
    ui.read_file(path, append_history=False)


def get_subset_sizes(path_optimiser: Path) -> tuple[int, int]:
    path_optimiser = Path(path_optimiser)
    if path_optimiser.exists():
        optimier = read_star(path_optimiser).first().trust_single()
        size = int(optimier.get("rlnSgdSubsetSize", -1))
        fin_size = int(optimier.get("rlnSgdFinalSubsetSize", -1))
        if size <= 0:
            size = fin_size
    else:
        size, fin_size = -1, -1
    if fin_size < 0:
        stem = path_optimiser.stem
        data_name = stem[: -len("_optimiser")] + "_data.star"
        data_file = path_optimiser.parent / data_name
        if data_file.exists():
            part = ParticleMetaModel.validate_file(data_file)
            fin_size = len(part.particles.block)
    if size < 0:
        size = fin_size
    return size, fin_size


def wait_for_file(path, num_retry: int = 5, delay: float = 0.1) -> bool:
    """Wait for a file to be created, return False if failed."""
    path = Path(path)
    for _ in range(num_retry):
        if path.exists():
            return True
        time.sleep(delay)
    return False


def monospace_font_family() -> str:
    """Get the system monospace font family."""
    if sys.platform.startswith("linux"):
        # In linux, "Monospace" sometimes falls back to Sans Serif.
        # Here, we try to find a better monospace font.
        font_family = _monospace_font_for_linux()
    else:
        font_family = MonospaceFontFamily
    return font_family


@lru_cache(maxsize=1)
def _monospace_font_for_linux() -> str:
    candidates = ["Noto Sans Mono", "DejaVu Sans Mono", "Ubuntu Mono"]
    families = QtGui.QFontDatabase.families()
    for fam in candidates:
        if fam in families:
            return fam
    return MonospaceFontFamily
