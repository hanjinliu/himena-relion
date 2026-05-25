import numpy as np
from numpy.typing import NDArray
from himena_relion import _utils


def project_fiducials(
    fid: NDArray[np.floating],
    tomo_center: NDArray[np.floating],
    deg: NDArray[np.floating],
    xf: NDArray[np.floating],
    tilt_center: NDArray[np.floating],
) -> NDArray[np.floating]:
    """Project 3D fiducial (zyx) to 2D (iyx)."""
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
