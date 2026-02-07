import subprocess
from typing import Annotated
import mrcfile
import numpy as np

from himena_relion._job_class import connect_jobs
from himena_relion.external import RelionExternalJob
from himena_relion._annotated.io import IN_PARTICLES, MAP_TYPE, IN_MASK
from himena_relion.relion5.extensions.transform import widgets as _wdg
from himena_relion.relion5._builtins import Refine3DJob
from . import _const as _c
from scipy import ndimage as ndi

SHIFT_BY = Annotated[
    str,
    {
        "choices": [
            ("Pixel", "pixel"),
            ("Angstrom", "angstrom"),
            ("Map center of mass", "map-com"),
            ("Mask center of mass", "mask-com"),
        ],
        "label": "Shift by",
        "tooltip": (
            "Unit of the shift value.\n"
            "<ul>"
            "<li><b>Pixel</b>: Shift by the specified number of pixels.</li>"
            "<li><b>Angstrom</b>: Shift by the specified number of angstroms.</li>"
            "<li><b>Map center of mass</b>: Shift the center of mass of the map.</li>"
            "<li><b>Mask center of mass</b>: Shift the center of mass of the mask.</li>"
            "</ul>"
        ),
    },
]
SHIFT = Annotated[
    tuple[float, float, float],
    {
        "label": "Shift (X, Y, Z)",
        "tooltip": "Shift values in the unit specified by the 'Shift by' option.",
    },
]


class ShiftMapJob(RelionExternalJob):
    """Shift a density map and the corresponding particles."""

    def output_nodes(self):
        return [
            (_c.OUTPUT_PARTICLES, "ParticleGroupMetadata.star"),
            (_c.OUTPUT_MAP, "DensityMap.mrc"),
        ]

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5:{cls.__name__}"

    @classmethod
    def job_title(cls):
        return "Shift Map"

    def run(
        self,
        in_3dref: MAP_TYPE = "",  # path
        in_parts: IN_PARTICLES = "",  # path
        in_mask: IN_MASK = "",
        shift_by: SHIFT_BY = "pixel",
        shift: SHIFT = (0.0, 0.0, 0.0),
    ):
        out_job_dir = self.output_job_dir
        if shift_by == "pixel":
            shift_pix = shift
        elif shift_by == "angstrom":
            _, scale = _read_image(in_3dref)
            shift_pix = tuple(s / scale for s in shift)
        elif shift_by == "map-com":
            shift_pix = self._shift_by_com(in_3dref)
        elif shift_by == "mask-com":
            shift_pix = self._shift_by_com(in_mask)
        else:
            raise ValueError(f"Invalid value for shift_by: {shift_by}")
        _shift_image(in_3dref, out_job_dir.path / _c.OUTPUT_MAP, shift_pix)
        self.console.log(f"Write shifted map to {out_job_dir.path / _c.OUTPUT_MAP}")
        if in_mask:
            _shift_image(in_mask, out_job_dir.path / _c.OUTPUT_MASK, shift_pix)
            self.console.log(
                f"Write shifted mask to {out_job_dir.path / _c.OUTPUT_MASK}"
            )
        if in_parts:
            _shift_star(in_parts, out_job_dir.path / _c.OUTPUT_PARTICLES, shift_pix)
            self.console.log(
                f"Write shifted partiles to {out_job_dir.path / _c.OUTPUT_PARTICLES}"
            )

    def provide_widget(self, job_dir):
        return _wdg.QShiftMapViewer(job_dir)

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["shift_by"].changed.connect
        def _on_shift_by_changed(val):
            enabled = val not in ["map-com", "mask-com"]
            widgets["shift"].enabled = enabled

        _on_shift_by_changed(widgets["shift_by"].value)

    def _shift_by_com(self, path):
        img, _ = _read_image(path)
        com = _img_center_of_mass(img)
        self.console.log(f"Center of mass of image {path}: {com}")
        center = tuple((s - 1) / 2 for s in img.shape)
        return tuple(float(c - cm) for c, cm in zip(center, com))


def _shift_image(path_in, path_out, shift):
    """Shift image using `relion_image_handler`"""
    img, pixel_size = _read_image(path_in)
    shift_zyx = (shift[2], shift[1], shift[0])
    img = img.astype(np.float32)
    cval = np.min(img)
    shifted = ndi.shift(img, shift=shift_zyx, order=3, mode="constant", cval=cval)
    with mrcfile.new(path_out, overwrite=True) as mrc:
        mrc.set_data(shifted)
        mrc.voxel_size = pixel_size


def _shift_star(path_in, path_out, shift):
    args_star = [
        _c.RELION_STAR_HANDLER,
        "--i",
        str(path_in),
        "--o",
        str(path_out),
        "--center",
        "--center_X",
        str(-shift[0]),
        "--center_Y",
        str(-shift[1]),
        "--center_Z",
        str(-shift[2]),
    ]
    subprocess.run(args_star, check=True)


def _img_center_of_mass(img: np.ndarray) -> tuple[float, float, float]:
    """Calculate the center of mass (X, Y, Z) of the image."""
    total = img.sum()
    if total == 0:
        return (0.0, 0.0, 0.0)
    z, y, x = np.indices(img.shape)
    com_z = (z * img).sum() / total
    com_y = (y * img).sum() / total
    com_x = (x * img).sum() / total
    return (com_x, com_y, com_z)


def _read_image(path) -> tuple[np.ndarray, float]:
    """Read image and its pixel size from the given path."""
    with mrcfile.open(path, mode="r") as mrc:
        img = mrc.data
        pixel_size = mrc.voxel_size.x  # assuming isotropic voxels
    return img, pixel_size


connect_jobs(
    Refine3DJob,
    ShiftMapJob,
    node_mapping={
        "run_class001.mrc": "in_3dref",
        "run_data.star": "in_parts",
    },
)
