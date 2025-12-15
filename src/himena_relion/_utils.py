from __future__ import annotations
from pathlib import Path
from typing import Annotated, Any

import numpy as np
from numpy.typing import NDArray
from functools import lru_cache
import starfile


def bin_image(img: np.ndarray, nbin: int) -> np.ndarray:
    """Bin a 2D image by an integer factor."""
    ny, nx = img.shape
    nyb = ny // nbin
    nxb = nx // nbin
    img = img[: nyb * nbin, : nxb * nbin]
    return img.reshape(nyb, nbin, nxb, nbin).mean(axis=(1, 3))


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
def threshold_yen(image: np.ndarray, nbins=256):
    counts, edges = np.histogram(
        image.reshape(-1),
        nbins,
        density=False,
    )
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
    return bin_centers[crit.argmax()]


def read_icon_svg(name: str) -> str:
    path = Path(__file__).parent / "resources" / f"{name}.svg"
    return path.read_text(encoding="utf-8")


def make_tilt_projection_mat(deg: float) -> NDArray[np.float32]:
    rad = np.deg2rad(deg)
    cos = np.cos(rad)
    sin = np.sin(rad)
    return np.array([[cos, 0, -sin], [0, 1, 0], [sin, 0, cos]], dtype=np.float32)


def last_job_directory() -> str:
    df = starfile.read("default_pipeline.star")
    path_last = df["pipeline_processes"]["rlnPipeLineProcessName"].iloc[-1]
    return path_last


def unwrapped_annotated(annot: Any) -> Any:
    origin = getattr(annot, "__origin__", None)
    if origin is Annotated:
        args = annot.__args__
        base_type = args[0]
        return base_type
    else:
        return annot
