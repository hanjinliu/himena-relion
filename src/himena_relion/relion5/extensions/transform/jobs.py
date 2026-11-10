from pathlib import Path
import shutil
import subprocess
from typing import Annotated
import mrcfile
import numpy as np
from starfile_rs import empty_star, read_star

from himena_relion._job_class import connect_jobs
from himena_relion.consts import MenuId
from himena_relion.external import RelionExternalJob
from himena_relion._annotated.io import IN_PARTICLES, MAP_TYPE, IN_MASK
from himena_relion.relion5.extensions.transform import widgets as _wdg
from himena_relion.relion5._builtins import Refine3DJob
from . import _const as _c
from scipy import ndimage as ndi

_PARTICLES = "particles"
_STAR_HEADER = "\n# version 50001\n"

CENTER_BY = Annotated[
    str,
    {
        "choices": [
            ("Pixel", "pixel"),
            ("Angstrom", "angstrom"),
            ("Map center of mass", "map-com"),
            ("Mask center of mass", "mask-com"),
        ],
        "label": "Center by",
        "tooltip": (
            "Unit of the shift value.\n"
            "<ul>"
            "<li><b>Pixel</b>: Shift by the specified number of pixels <b>in the input "
            "3D map</b>.</li>"
            "<li><b>Angstrom</b>: Shift by the specified number of angstroms.</li>"
            "<li><b>Map center of mass</b>: Shift the center of mass of the map.</li>"
            "<li><b>Mask center of mass</b>: Shift the center of mass of the mask.</li>"
            "</ul>"
        ),
    },
]
NEW_CENTER = Annotated[
    tuple[float, float, float],
    {
        "label": "New center (X, Y, Z)",
        "tooltip": "New center of the map in the unit specified by the option above.",
    },
]


class ShiftMapJob(RelionExternalJob):
    """Shift a density map and the corresponding particles."""

    OUTPUT_PARTICLES = _c.OUTPUT_PARTICLES
    OUTPUT_MAP = _c.OUTPUT_MAP

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

    @classmethod
    def menu_id(cls):
        return MenuId.RELION_UTILS_JOB

    def run(
        self,
        in_3dref: MAP_TYPE = "",  # path
        in_parts: IN_PARTICLES = "",  # path
        in_mask: IN_MASK = "",
        center_by: CENTER_BY = "pixel",
        new_center: NEW_CENTER = (0.0, 0.0, 0.0),
    ):
        out_job_dir = self.output_job_dir
        if center_by == "pixel":
            _, scale = _read_image(in_3dref)
            new_center_pix = new_center
            new_center_ang = tuple(s * scale for s in new_center_pix)
        elif center_by == "angstrom":
            _, scale = _read_image(in_3dref)
            new_center_pix = tuple(s / scale for s in new_center)
            new_center_ang = new_center
        elif center_by == "map-com":
            new_center_pix, new_center_ang = _center_by_com(in_3dref)
        elif center_by == "mask-com":
            new_center_pix, new_center_ang = _center_by_com(in_mask)
        else:
            raise ValueError(f"Invalid value for center_by: {center_by}")

        self.console.log(f"Shift in pixels: {_round_shift(new_center_pix)}")
        self.console.log(f"Shift in angstroms: {_round_shift(new_center_ang)}")
        _shift_image(in_3dref, out_job_dir.path / _c.OUTPUT_MAP, new_center_pix)
        self.console.log(f"Write shifted map to {out_job_dir.path / _c.OUTPUT_MAP}")
        if in_mask:
            _shift_image(
                in_mask, out_job_dir.path / _c.OUTPUT_MASK, new_center_pix, clip=(0, 1)
            )
            self.console.log(
                f"Write shifted mask to {out_job_dir.path / _c.OUTPUT_MASK}"
            )
        if in_parts:
            _shift_star(
                in_parts, out_job_dir.path / _c.OUTPUT_PARTICLES, new_center_ang
            )
            self.console.log(
                f"Write shifted partiles to {out_job_dir.path / _c.OUTPUT_PARTICLES}"
            )

    def provide_widget(self, job_dir):
        return _wdg.QShiftMapViewer(job_dir)

    @classmethod
    def setup_widgets(cls, widgets):
        @widgets["center_by"].changed.connect
        def _on_center_by_changed(val):
            enabled = val not in ["map-com", "mask-com"]
            widgets["new_center"].enabled = enabled

        _on_center_by_changed(widgets["center_by"].value)


def _center_by_com(
    path,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    img, img_scale = _read_image(path)
    com = _img_center_of_mass(img)
    center = tuple((s - 1) / 2 for s in img.shape)
    out_pix = tuple(float(c - cm) for c, cm in zip(center, com))
    out_angst = tuple(d * img_scale for d in out_pix)
    return out_pix, out_angst


def _shift_image(path_in, path_out, shift_pix, clip=None):
    """Shift image using scipy."""
    img, pixel_size = _read_image(path_in)
    shift_zyx = (shift_pix[2], shift_pix[1], shift_pix[0])
    img = img.astype(np.float32)
    cval = np.min(img)
    shifted = ndi.shift(img, shift=shift_zyx, order=3, mode="constant", cval=cval)
    if clip:
        shifted = np.clip(shifted, clip[0], clip[1])
    with mrcfile.new(path_out, overwrite=True) as mrc:
        mrc.set_data(shifted)
        mrc.voxel_size = pixel_size


def _shift_star(path_in, path_out, shift_ang):
    """Use relion_star_handler to shift the particle coordinates.

    Note that relion_star_handler uses the optics block in the input star file to
    determine the pixel size, but this causes confusion when the scale of particle
    images and the input map are different. Therefore, we set the pixel size to 1 and
    directly specify the shift in angstroms, along with the `--ignore_optics` option to
    ignore the optics block. The raw output of relion_star_handler, which does not have
    the optics block, is kept next to the final output.
    """
    path_no_optics = Path(path_out).with_name(_c.OUTPUT_PARTICLES_NO_OPTICS)
    args_star = [
        _c.RELION_STAR_HANDLER,
        "--i",
        str(path_in),
        "--o",
        str(path_no_optics),
        "--center",
        "--center_X",
        str(-shift_ang[0]),
        "--center_Y",
        str(-shift_ang[1]),
        "--center_Z",
        str(-shift_ang[2]),
        "--angpix",
        "1",
        "--ignore_optics",
    ]
    subprocess.run(args_star, check=True)
    _restore_optics(path_in, path_no_optics, path_out)


def _restore_optics(path_in, path_no_optics, path_out):
    """Write the star file with the optics block of the input star file restored.

    `relion_star_handler --ignore_optics` writes only the particles table, which makes
    the output unusable for the jobs that need the optics groups (such as joining star
    files). Shifting the origins does not change any of the optics parameters, so that
    the input optics block can be reused as is.
    """
    star_in = read_star(path_in)
    star_handled = read_star(path_no_optics)
    if star_in.get("optics") is None or star_handled.get("optics") is not None:
        # star file without optics groups (before RELION 3.1), or nothing to restore
        shutil.copyfile(path_no_optics, path_out)
        return
    if star_handled.get(_PARTICLES) is None:
        star_handled = star_handled.rename({star_handled.first().name: _PARTICLES})
    star_out = empty_star()
    for name in ["general", "optics"]:
        if (blk := star_in.get(name)) is not None:
            star_out.with_block(blk)
    star_out.with_block(star_handled[_PARTICLES])
    text = _STAR_HEADER + star_out.to_string()
    Path(path_out).write_text(text, newline="\n")


def _img_center_of_mass(img: np.ndarray) -> tuple[float, float, float]:
    """Calculate the center of mass (X, Y, Z) of the image."""
    total = img.sum()
    if total == 0:
        return (0.0, 0.0, 0.0)
    z, y, x = np.indices(img.shape)
    com_z = (z * img).sum() / total
    com_y = (y * img).sum() / total
    com_x = (x * img).sum() / total
    return (float(com_x), float(com_y), float(com_z))


def _read_image(path) -> tuple[np.ndarray, float]:
    """Read image and its pixel size from the given path."""
    with mrcfile.open(path, mode="r") as mrc:
        img = mrc.data
        pixel_size = mrc.voxel_size.x  # assuming isotropic voxels
    return img, float(pixel_size)


def _round_shift(shift_pix):
    return tuple(round(s, 2) for s in shift_pix)


connect_jobs(
    Refine3DJob,
    ShiftMapJob,
    node_mapping={
        "run_class001.mrc": "in_3dref",
        "run_data.star": "in_parts",
    },
)
