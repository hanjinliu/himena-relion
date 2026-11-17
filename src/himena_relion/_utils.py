from __future__ import annotations

from contextlib import contextmanager, suppress
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
import logging
import time
from typing import (
    Annotated,
    Any,
    Iterable,
    Iterator,
    TextIO,
    get_args,
    get_origin,
    TYPE_CHECKING,
)
from functools import lru_cache

import numpy as np
import polars as pl

from himena.types import is_subtype
from himena_relion.consts import (
    Type,
    DEFAULT_PIPELINE_BACKUP,
    DEFAULT_PIPELINE_STAR,
    PIPELINE_NODE_NAME,
)
from himena_relion.schemas import RelionPipelineModel
from himena_relion._configs import get_relion_pipeliner_exe
from himena_relion._wsl import is_wsl_path, wsl_prefix

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from himena import MainWindow
    from himena_relion.pipeline.widgets import QRelionPipelineFlowChart

_LOGGER = logging.getLogger(__name__)


def write_text_lf(path: str | Path, text: str) -> None:
    """Write text with LF line endings, even on Windows.

    RELION cannot read files with CRLF line endings, which is the default of
    `Path.write_text` on Windows.
    """
    Path(path).write_text(text, newline="\n")


def write_bytes_atomic(
    path: str | Path,
    data: bytes,
    *,
    replace_timeout: float = 2.0,
) -> None:
    """Replace the content of a file so that it is never empty or partially written.

    `data` is written to a temporary file in the same directory, which then replaces
    `path` by `os.replace`. Readers see either the old or the new content, and `path`
    is left unchanged if anything fails (or the process is killed) before that.

    On Windows, `os.replace` fails while another process has `path` open (e.g. a
    pipeline watcher reading it), so it is retried for `replace_timeout` seconds. If it
    still fails, `path` is overwritten in place. The new content is written before the
    rest of the file is truncated, so that it does not become empty in that case either.
    """
    path = Path(path)
    try:
        tmp = _write_temp_file(path, data)
    except PermissionError:
        # e.g. the file is writable but its directory is not
        _overwrite_in_place(path, data)
        return
    try:
        if not _replace_with_retry(tmp, path, replace_timeout):
            _LOGGER.warning("Could not replace %s, overwriting it in place.", path)
            _overwrite_in_place(path, data)
    finally:
        tmp.unlink(missing_ok=True)


def write_text_atomic(path: str | Path, text: str) -> None:
    """Write text in UTF-8 atomically (see `write_bytes_atomic`), keeping newlines."""
    write_bytes_atomic(path, text.encode("utf-8"))


def _write_temp_file(path: Path, data: bytes) -> Path:
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            with suppress(OSError):
                os.fsync(f.fileno())
        _copy_permissions(path, tmp)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return tmp


def _copy_permissions(src: Path, dst: Path) -> None:
    """Give the temporary file `dst` the permissions of the file it will replace.

    `mkstemp` creates files only accessible by the owner, which would prevent other
    users from running jobs in a shared project.
    """
    try:
        st = src.stat()
    except FileNotFoundError:
        # a new file: same as the directory but not executable
        mode = stat.S_IMODE(src.parent.stat().st_mode) & 0o666
        gid = None
    else:
        mode = stat.S_IMODE(st.st_mode)
        gid = st.st_gid
    with suppress(OSError):
        os.chmod(dst, mode)
    if gid is not None and hasattr(os, "chown"):
        with suppress(OSError):
            os.chown(dst, -1, gid)


def _replace_with_retry(src: Path, dst: Path, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        try:
            os.replace(src, dst)
        except PermissionError:
            # On Windows, `dst` is opened by another process.
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.01)
        else:
            return True


def _overwrite_in_place(path: Path, data: bytes) -> None:
    try:
        f = path.open("r+b")
    except FileNotFoundError:
        f = path.open("xb")
    with f:
        f.write(data)  # write first, so that the file is never empty
        f.truncate()
        f.flush()
        with suppress(OSError):
            os.fsync(f.fileno())


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
    """Apply a low-pass filter to a 2D or 3D image in Fourier space."""
    if cutoff <= 0 or cutoff >= 0.9:
        return img
    if img.ndim == 2:
        fr = frequency_mesh(img.shape)
    elif img.ndim == 3:
        fr = frequency_mesh_3d(img.shape)
    else:
        raise ValueError(f"Expected 2D or 3D image, got {img.ndim}D")
    filter_mask = fr <= cutoff
    img_ft = np.fft.fftn(img)
    img_ft_filtered = img_ft * filter_mask
    img_filtered = np.fft.ifftn(img_ft_filtered).real
    return img_filtered


@lru_cache(maxsize=32)
def frequency_mesh(shape: tuple[int, int]) -> np.ndarray:
    """Generate a frequency mesh for a given image shape."""
    fy, fx = np.fft.fftfreq(shape[0]), np.fft.fftfreq(shape[1])
    fxx, fyy = np.meshgrid(fx, fy)
    fr = np.sqrt(fxx**2 + fyy**2)
    return fr


@lru_cache(maxsize=4)
def frequency_mesh_3d(shape: tuple[int, int, int]) -> np.ndarray:
    """Generate a 3D frequency mesh for a given image shape."""
    fz, fy, fx = (
        np.fft.fftfreq(shape[0]),
        np.fft.fftfreq(shape[1]),
        np.fft.fftfreq(shape[2]),
    )
    fxx, fyy, fzz = np.meshgrid(fx, fy, fz)
    fr = np.sqrt(fxx**2 + fyy**2 + fzz**2)
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
        case "AtomCoords":
            return read_icon_svg("atom_coords")
        # case "Sequence":
        #     ...
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
    pipeline = RelionPipelineModel.validate_file(cwd / DEFAULT_PIPELINE_STAR)
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


def make_alias_link(rln_dir: Path, alias: str, job_id: str) -> None:
    """Create a symlink for the job alias, such as "Select/split -> ../Select/job035/".

    `alias` and `job_id` are the paths relative to the RELION project directory. The
    link target is relative, as RELION does. For WSL projects, the link is created in
    WSL because Windows cannot create symlinks in the WSL file system.
    """
    link = normalize_job_id(alias).rstrip("/")
    target = f"../{normalize_job_id(job_id)}"
    if is_wsl_path(rln_dir):
        proc = subprocess.run(
            [*wsl_prefix(rln_dir), "ln", "-s", target, link],
            capture_output=True,
        )
        if proc.returncode != 0:
            msg = proc.stderr.decode("utf-8", "replace").strip()
            raise OSError(f"Failed to create alias link {link!r}: {msg}")
    else:
        rln_dir.joinpath(link).symlink_to(target, target_is_directory=True)


def remove_alias_link(rln_dir: Path, alias: str) -> None:
    """Remove the symlink for the job alias if exists."""
    link = normalize_job_id(alias).rstrip("/")
    if is_wsl_path(rln_dir):
        # Symlinks in WSL are not recognized as symlinks from Windows.
        subprocess.run(
            [*wsl_prefix(rln_dir), "rm", link],
            check=True,
            capture_output=True,
        )
    elif (alias_path := rln_dir / link).is_symlink():
        alias_path.unlink()


class PipelineFile:
    """A pipeline STAR file that is read and rewritten as a whole.

    This is what `open_with_lock` yields. Unlike a file object, `write` replaces the
    file atomically (see `write_bytes_atomic`), so that the file never becomes empty
    or partially written, even if an error occurs or the process is killed. If
    `backup` is given, the current content is saved there before it is rewritten.
    """

    def __init__(self, path: str | Path, backup: str | Path | None = None):
        self.path = Path(path)
        self._backup = None if backup is None else Path(backup)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.path.as_posix()!r})"

    @property
    def name(self) -> str:
        return str(self.path)

    def read(self) -> str:
        """Read the whole content (UTF-8, newlines are not translated)."""
        return self.path.read_bytes().decode("utf-8")

    def write(self, text: str) -> None:
        """Replace the whole content with `text`."""
        if self._backup is not None:
            _backup_pipeline(self.path, self._backup)
        write_text_atomic(self.path, text)


def _backup_pipeline(path: Path, backup: Path) -> None:
    try:
        data = path.read_bytes()
        # do not overwrite the last good backup with a broken file
        if b"data_pipeline_general" in data:
            write_bytes_atomic(backup, data)
    except Exception:
        _LOGGER.warning("Failed to back up %s", path, exc_info=True)


def _read_pipeline_text(f: PipelineFile | TextIO) -> str:
    if not isinstance(f, PipelineFile):
        f.seek(0)
    return f.read()


def _write_pipeline_text(f: PipelineFile | TextIO, text: str) -> None:
    """Replace the content of a pipeline file.

    A plain file object is overwritten in place. The new text is written before the
    rest is truncated, so that the file does not become empty if writing fails.
    """
    if isinstance(f, PipelineFile):
        f.write(text)
    else:
        f.seek(0)
        f.write(text)
        f.truncate()


def update_default_pipeline(
    f: PipelineFile | TextIO,
    job_id: str | Path,
    state: str | None = None,
    alias: str | None = None,
    *,
    check_state: bool = True,
):
    """Update the status and/or the alias of a job in a pipeline STAR file.

    Problems in reading the pipeline (broken file, job not found etc.) are logged and
    the file is left unchanged. Errors in writing the file are raised.
    """
    if (
        check_state
        and state is not None
        and state not in ("Scheduled", "Running", "Failed", "Succeeded", "Aborted")
    ):
        raise ValueError(f"State {state!r} is not a valid RELION job state.")
    job_id = normalize_job_id(job_id)
    try:
        pipeline_star = RelionPipelineModel.validate_text(_read_pipeline_text(f))
        matched = np.where(pipeline_star.processes.process_name == job_id)[0]
        if len(matched) == 0:
            _LOGGER.warning("%s not found in pipeline", job_id)
            return
        row = int(matched[0])
        df = pipeline_star.processes.dataframe
        if state is not None:
            df[row, df.columns.index("rlnPipeLineProcessStatusLabel")] = state
        if alias is not None:
            df[row, df.columns.index("rlnPipeLineProcessAlias")] = alias
        pipeline_star.processes = df
        # The text must be ready before the file is modified.
        text = pipeline_star.to_string()
    except Exception:
        _LOGGER.warning("Failed to update job state for %s", job_id, exc_info=True)
        return
    _write_pipeline_text(f, text)


def _assert_input_edge(val) -> str:
    if not isinstance(val, str):
        raise ValueError(f"Expected input edge to be a string, got {type(val)}")
    return val


def replace_input_edges(
    f: PipelineFile | TextIO,
    to_run: str,
    new_inputs: Iterable[str] = (),
    default_pipeline: str | Path | None = None,
):
    """Replace input edges in the pipeline STAR for overwriting/continuing jobs.

    Parameters
    ----------
    f : PipelineFile or TextIO
        The pipeline STAR file to be modified.
    to_run : str
        The job identifier (e.g. "Refine3D/job010/") for which the input edges will be
        updated
    new_inputs : Iterable[str], optional
        The new input edges (from_node) for the job `to_run`. If empty, the input edges
        will not be edited.
    default_pipeline : path-like, optional
        The path to the default_pipeline.star file.
    """
    pipeline_model = RelionPipelineModel.validate_text(_read_pipeline_text(f))
    to_run = normalize_job_id(to_run)
    pipeline_input_edges = pipeline_model.input_edges
    new_from_node = [_assert_input_edge(n) for n in new_inputs]
    if pipeline_input_edges.block.shape[0] > 0:
        indices = pipeline_input_edges.process == to_run
        df = pipeline_input_edges.dataframe.filter(~indices)
    else:
        df = pipeline_input_edges.dataframe
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
            ).nodes.dataframe.filter(pl.col(PIPELINE_NODE_NAME).is_in(new_from_node))
            nodes_this = pipeline_model.nodes.dataframe.filter(
                # NOTE: cast is needed because the column is Null type if empty
                pl.col(PIPELINE_NODE_NAME).cast(pl.String).str.starts_with(to_run)
            )
            pipeline_model.nodes = pl.concat(
                [nodes_full, nodes_this], how="vertical_relaxed"
            )

    pipeline_model.input_edges = df
    _write_pipeline_text(f, pipeline_model.to_string())


def read_or_show_job(ui: MainWindow, path: Path):
    """Open a RELION job file in the UI, or switch to it if already opened."""
    from himena_relion._job_dir import JobDirectory

    if path.is_file() and path.name == "job.star":
        path = path.parent
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


def invert_y(img):
    """Most of the 2D image viewers (such as 3dmod) invert the Y axis."""
    return img[::-1]


@contextmanager
def relion_lock(relion_project_dir: str | Path, wait_sec: float = 1.5):
    """Hold the RELION lock `.relion_lock/` of the project.

    RELION creates this directory before reading the pipeline to edit it, and removes
    it after writing (`PipeLine::read/write` with DO_LOCK). Raises
    `RelionPipelineLockError` if the lock is not acquired within `wait_sec` seconds.
    """
    lock_dir = Path(relion_project_dir) / ".relion_lock"
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
            f"Failed to acquire the lock {lock_dir}. Another instance may be editing "
            "the pipeline, or the previous run may have crashed."
        )
    try:
        yield
    finally:
        with suppress(Exception):
            lock_dir.rmdir()


@contextmanager
def open_with_lock(
    pipeline_path: str | Path,
    wait_sec: float = 1.5,
) -> Iterator[PipelineFile]:
    """Edit a pipeline STAR file while holding the RELION lock.

    The yielded `PipelineFile` replaces the file atomically, so that RELION and the
    pipeline watchers never read an empty or partially written file. The content of
    default_pipeline.star before each edit is saved to `DEFAULT_PIPELINE_BACKUP`. The
    file is touched after the lock is released, to notify the watchers.
    """
    pipeline_path = Path(pipeline_path)
    if pipeline_path.name == DEFAULT_PIPELINE_STAR:
        backup = pipeline_path.with_name(DEFAULT_PIPELINE_BACKUP)
    else:
        backup = None
    lock_acquired = False
    try:
        with relion_lock(pipeline_path.parent, wait_sec=wait_sec):
            lock_acquired = True
            yield PipelineFile(pipeline_path, backup=backup)
    finally:
        if lock_acquired:
            with suppress(Exception):
                pipeline_path.touch()


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
