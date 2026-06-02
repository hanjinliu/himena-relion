from __future__ import annotations

from contextlib import contextmanager, suppress
import os
import shutil
from pathlib import Path
import logging
import time
from typing import Annotated, Any, Iterable, TextIO, get_args, get_origin, TYPE_CHECKING
from functools import lru_cache

import numpy as np
import polars as pl

from himena.types import is_subtype
from himena_relion.consts import Type
from himena_relion.schemas import RelionPipelineModel
from himena_relion._configs import get_relion_pipeliner_exe

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from himena import MainWindow
    from himena_relion.pipeline.widgets import QRelionPipelineFlowChart

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
    if cutoff <= 0 or cutoff >= 0.9:
        return img
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
    nbins = max(min(nbins, input_arr.size), 1)
    counts, edges = np.histogram(input_arr, nbins, density=False)
    bin_centers = (edges[:-1] + edges[1:]) / 2

    # On blank images (e.g. filled with 0) with int dtype, `histogram()`
    # returns ``bin_centers`` containing only one value. Speed up with it.
    if bin_centers.size == 1:
        return bin_centers[0]

    # Calculate probability mass function
    counts_sum = counts.sum()
    if counts_sum == 0:
        return float(bin_centers[0])
    pmf = counts.astype("float32", copy=False) / counts_sum
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
        case "Image2DGroupMetadata":
            return read_icon_svg("classes")
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


def last_job_directory(cwd: Path | None = None) -> str:
    """Get the identifier of the latest job."""
    if cwd is None:
        cwd = Path.cwd()
    pipeline = RelionPipelineModel.validate_file(cwd / "default_pipeline.star")
    return pipeline.processes.process_name[-1]


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
    f: TextIO,
    job_id: str,
    state: str | None = None,
    alias: str | None = None,
    *,
    check_state: bool = True,
):
    if (
        check_state
        and state is not None
        and state not in ("Scheduled", "Running", "Failed", "Succeeded", "Aborted")
    ):
        raise ValueError(f"State {state!r} is not a valid RELION job state.")
    f.seek(0)
    try:
        pipeline_star = RelionPipelineModel.validate_text(f.read())
        pos_sl = pipeline_star.processes.process_name == normalize_job_id(job_id)
        if len(true_ids := np.where(pos_sl)) == 1:
            if len(true_ids[0]) == 0:
                _LOGGER.warning("%s not found in pipeline", normalize_job_id(job_id))
                return
            true_id = int(true_ids[0][0])
            df = pipeline_star.processes.dataframe
            if state is not None:
                ic = df.columns.index("rlnPipeLineProcessStatusLabel")
                df[true_id, ic] = state
            if alias is not None:
                ic = df.columns.index("rlnPipeLineProcessAlias")
                df[true_id, ic] = alias
            pipeline_star.processes = df
            f.seek(0)
            f.truncate(0)
            f.write(pipeline_star.to_string())
    except Exception:
        _LOGGER.warning("Failed to update job state for %s", job_id, exc_info=True)


def _assert_input_edge(val) -> str:
    if not isinstance(val, str):
        raise ValueError(f"Expected input edge to be a string, got {type(val)}")
    return val


def replace_input_edges(
    f: TextIO,
    to_run: str,
    new_inputs: Iterable[str] = (),
    default_pipeline: str | Path | None = None,
):
    f.seek(0)
    pipeline_model = RelionPipelineModel.validate_text(f.read())
    to_run = normalize_job_id(to_run)
    pipeline_input_edges = pipeline_model.input_edges
    new_from_node = [_assert_input_edge(n) for n in new_inputs]
    if pipeline_input_edges is not None:
        indices = pipeline_input_edges.process == to_run
        df = pipeline_input_edges.dataframe.filter(~indices)
    else:
        df = RelionPipelineModel.InputEdges(from_node=[], process=[]).dataframe
    if new_from_node:
        df_new = pipeline_model.InputEdges(
            from_node=new_from_node,
            process=[to_run] * len(new_from_node),
        ).dataframe
        df = pl.concat([df, df_new], how="vertical_relaxed")

        # when updating job_pipeline.star, we need to update the node info based on the
        # default_pipeline.star as well.
        if default_pipeline:
            nodes_full = RelionPipelineModel.validate_file(
                default_pipeline
            ).nodes.dataframe.filter(pl.col("rlnPipeLineNodeName").is_in(new_from_node))
            nodes_this = pipeline_model.nodes.dataframe.filter(
                pl.col("rlnPipeLineNodeName").str.starts_with(to_run)
            )
            pipeline_model.nodes = pl.concat(
                [nodes_full, nodes_this], how="vertical_relaxed"
            )

    pipeline_model.input_edges = df
    f.seek(0)
    f.truncate()
    f.write(pipeline_model.to_string())


def read_or_show_job(ui: MainWindow, path: Path):
    """Open a RELION job file in the UI, or switch to it if already opened."""
    from himena_relion._job_dir import JobDirectory

    # if already opened, switch to it
    for i_tab, tab in ui.tabs.enumerate():
        for i_window, window in tab.enumerate():
            mtype = window.model_type() or "not_a_relion_job"
            if not is_subtype(mtype, Type.RELION_JOB):
                continue
            try:
                val = window.value
                if isinstance(val, JobDirectory) and path == val.path:
                    ui.tabs.current_index = i_tab
                    tab.current_index = i_window
                    return
            except Exception:
                continue
    ui.set_status_tip(f"Opening job: {path.name}", process_event=True)
    ui.read_file(path, append_history=False)


def wait_for_file(path, num_retry: int = 5, delay: float = 0.1) -> bool:
    """Wait for a file to be created, return False if failed.

    Examples
    --------
    ```python
    if wait_for_file(path, num_retry=100, delay=0.3):
        # do something
    ```
    """
    path = Path(path)
    for _ in range(num_retry):
        if path.exists():
            return True
        time.sleep(delay)
    return False


def get_pipeline_widgets(
    ui: MainWindow,
    relion_project_dir: Path | None = None,
) -> QRelionPipelineFlowChart | None:
    """Return the currently active pipeline widget if exists."""
    from himena_relion.pipeline.widgets import QRelionPipelineFlowChart

    for dock in ui.dock_widgets:
        if isinstance(flowchart := dock.widget, QRelionPipelineFlowChart):
            dir_for_this = flowchart._relion_project_dir
            if dir_for_this == relion_project_dir or relion_project_dir is None:
                return dock.widget


def open_url(url: str) -> None:
    """Open the URL with the default browser."""
    import webbrowser

    webbrowser.open(url)


def iter_directory_content_summary(path: Path, yield_every: int = 5000):
    # NOTE: Path.walk is not available in Python 3.11, and using os.walk is faster.
    num_files = 0
    total_size_bytes = 0
    yield num_files, total_size_bytes
    for root, _dirs, files in os.walk(str(path)):
        for file in files:
            num_files += 1
            try:
                total_size_bytes += os.path.getsize(os.path.join(root, file))
            except Exception:
                continue  # e.g. file deleted during walk
            if num_files % yield_every == 0:
                yield num_files, total_size_bytes
    if num_files % yield_every != 0:
        yield num_files, total_size_bytes


def command_not_found_err_msg(first_sentense: str):
    return (
        f"{first_sentense}. Please set a correct path in the config (Ctrl+,).\n"
        "See https://hanjinliu.github.io/himena-relion/getting_started/ for more "
        "details."
    )


def bytes_to_size_str(num_bytes: int) -> str:
    if num_bytes < 1024:
        size_str = f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        size_str = f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        size_str = f"{num_bytes / 1024**2:.1f} MB"
    else:
        size_str = f"{num_bytes / 1024**3:.1f} GB"
    return size_str


@contextmanager
def open_with_lock(
    pipeline_path: str | Path,
    mode: str = "r+",
    wait_sec: float = 1.5,
):
    """Open a file with a lock to prevent concurrent access."""
    pipeline_path = Path(pipeline_path)
    lock_dir = pipeline_path.parent / ".relion_lock"
    each_wait = 0.05
    num_trial = int(wait_sec / each_wait) + 1
    for _ in range(num_trial):
        try:
            lock_dir.mkdir(exist_ok=False)
        except FileNotFoundError:
            raise  # FileNotFoundError is a subclass of OSError.
        except OSError:
            time.sleep(each_wait)
        else:
            break
    else:
        raise RelionPipelineLockError(
            f"Failed to acquire lock for {pipeline_path}. Another instance may be "
            "editing the pipeline, or the previous run may have crashed. "
        )
    try:
        with pipeline_path.open(mode) as f:
            yield f
    finally:
        pipeline_path.touch()
        # remove the lock
        with suppress(Exception):
            lock_dir.rmdir()


def extract_input_edges(params: dict[str, str], keys: Iterable[str]) -> list[str]:
    """Used for input_edges method."""
    edges = []
    for key in keys:
        if val := params.get(key, "").strip():
            edges.append(val)
    return edges


class RelionPipelineLockError(RuntimeError):
    """Raised when failed to acquire lock for RELION default_pipeline.star file."""


def read_mod(path: str | Path) -> pl.DataFrame:
    import imodmodel

    return pl.DataFrame(imodmodel.read(path))


@lru_cache(maxsize=1)
def relion_python_executable() -> Path:
    """Get the path to the Python executable that RELION uses."""
    if pipeliner_path := shutil.which(get_relion_pipeliner_exe()):
        pipeliner_path = Path(pipeliner_path)
        # will be /path/to/relion/build/bin/relion_pipeliner
        # we want /path/to/relion/build/CMakeCache.txt
        cmake_cache_path = pipeliner_path.parent.parent / "CMakeCache.txt"
        if cmake_cache_path.exists():
            with cmake_cache_path.open() as f:
                for line in f:
                    if line.startswith("PYTHON_EXE_PATH:PATH="):
                        python_path = line.split("=", 1)[1].strip()
                        if python_path.strip():
                            return Path(python_path)
    if python_path := shutil.which("python"):
        return Path(python_path)
    raise RuntimeError(
        "Failed to find Python executable used by RELION. Please make sure RELION is "
        "installed and relion_pipeliner is in your PATH."
    )
