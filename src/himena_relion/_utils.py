from __future__ import annotations

import numpy as np
from functools import lru_cache


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
