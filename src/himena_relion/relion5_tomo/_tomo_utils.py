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


# 1    125.47    406.26     88.69      1    1 Pix:     8.00000 Dim:   464   480
# 2    148.21    261.18    -20.94      1    2
# 3    182.94    427.79     95.55      1    3
# 4     88.67    261.47     61.82      1    4
def read_xyz(fid: str) -> NDArray[np.floating]:
    """Read fiducial points from an IMOD .xyz file."""
    arr = []
    pix = 8.0
    with open(fid) as f:
        for line in f:
            if len(arr) == 0:  # first line contains Pix and Dim
                line, rem = line.split("Pix:")
                pix_str, rem = rem.strip().split("Dim:")
                pix = float(pix_str.strip())
                # dim_x_str, dim_y_str = rem.split()
                # dim = (int(dim_x_str.strip()), int(dim_y_str.strip()))
            vals = line.split()
            arr.append([float(vals[1]), float(vals[2]), float(vals[3])])
    return np.array(arr, dtype=np.float32) * pix
