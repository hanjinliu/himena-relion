from pathlib import Path
import subprocess

import numpy as np
from numpy.typing import NDArray
from himena_relion import _utils


def xf_to_array(xf: str | Path) -> NDArray[np.floating]:
    """Read transformation matrix from xf file."""
    with open(xf) as f:
        arr_str = [line.split() for line in f]
    return np.array(arr_str, dtype=np.float32)


def project_fiducials(
    fid: NDArray[np.floating],
    tomo_center: NDArray[np.floating],
    deg: NDArray[np.floating],
    xf: NDArray[np.floating],
    tilt_center: NDArray[np.floating],
) -> NDArray[np.floating]:
    fid_center = fid - tomo_center
    out = []
    for i, d in enumerate(deg):
        a11, a12, a21, a22, tx, ty = xf[i]
        mat_al = np.linalg.inv(np.array([[a22, a21], [a12, a11]]))
        for zyx in fid_center:
            zyx0 = _utils.make_tilt_projection_mat(d) @ zyx + tomo_center
            zyx0[1:] = mat_al @ (zyx0[1:] - [ty, tx] - tomo_center[1:]) + tilt_center
            zyx0[0] = i
            out.append(zyx0)
    return np.stack(out, axis=0)


def findbeads3d_wrapped(
    exe: str,
    tomo_path: str | Path,
    out_path: str | Path,
    size_pix: float,
    angle_range: tuple[float, float] = (-60.0, 60.0),
):
    # rec_TS_01_half1.mrc out.mod -angle "-60.0,60.0" -si 12
    a0, a1 = angle_range
    stdout_path = Path(out_path).with_suffix(".out")
    stderr_path = Path(out_path).with_suffix(".err")
    with open(stdout_path, "w") as stdout_file, open(stderr_path, "w") as stderr_file:
        out = subprocess.run(
            [
                exe,
                str(tomo_path),
                str(out_path),
                "-angle",
                f"{a0},{a1}",
                "-si",
                str(size_pix),
            ],
            stdout=stdout_file,
            stderr=stderr_file,
        )
    if out.returncode != 0:
        raise RuntimeError(f"findbeads3d failed with return code {out.returncode}")


def erase_gold(
    img: NDArray[np.floating],  # (H, W)
    pos: NDArray[np.floating],  # (N, 2)
    rng: np.random.Generator,
    gold_px: float = 10.0,
):
    # NOTE: float16 sometimes causes overflow in mean/std calculation
    img = img.astype(np.float32, copy=True)
    mask = np.zeros_like(img, dtype=bool)
    gold_px_int = int(np.ceil(gold_px))
    yy, xx = np.indices((gold_px_int, gold_px_int))
    yy = yy - gold_px / 2
    xx = xx - gold_px / 2
    rr: NDArray[np.floating] = np.sqrt(yy**2 + xx**2)
    circle_mask = rr <= (gold_px / 2)
    for yc, xc in pos:
        y0 = int(yc - gold_px / 2)
        x0 = int(xc - gold_px / 2)
        y_start = max(0, y0)
        x_start = max(0, x0)
        y_end = min(mask.shape[0], y0 + gold_px_int)
        x_end = min(mask.shape[1], x0 + gold_px_int)
        if x_end <= x_start or y_end <= y_start:
            continue

        mask_y_start = y_start - y0
        mask_x_start = x_start - x0
        mask_y_end = mask_y_start + (y_end - y_start)
        mask_x_end = mask_x_start + (x_end - x_start)
        mask_cropped = circle_mask[mask_y_start:mask_y_end, mask_x_start:mask_x_end]
        ref = img[y_start:y_end, x_start:x_end][~mask_cropped]
        if ref.size == 0:
            continue  # should never happen, but just in case
        mean = np.mean(ref)
        std = np.std(ref, mean=mean)
        img[y_start:y_end, x_start:x_end][mask_cropped] = rng.normal(
            mean, std, size=mask_cropped.sum()
        )

    return img.astype(np.float16)
