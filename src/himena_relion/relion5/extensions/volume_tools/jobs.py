from pathlib import Path
import time
import os
import shutil
from typing import Annotated

import mrcfile
import numpy as np

from himena.qt.magicgui import ToggleButtons
from himena_relion._job_class import connect_jobs
from himena_relion._proc import popen_detached
from himena_relion.consts import MenuId
from himena_relion.external import RelionExternalContinue, RelionExternalJob
from himena_relion._utils import (
    file_stamp,
    is_file_updated,
    lowpass_filter,
    relion_python_executable,
)
from himena_relion._annotated.io import MAP_TYPE
from himena_relion.relion5.extensions.volume_tools.widgets import QMaskCreateViewer
from himena_relion.relion5._connections import mask_create_search_halfmap
from himena_relion.relion5 import _builtins as _spa

_USE_APP = Annotated[
    str,
    {
        "label": "Application to use",
        "choices": ["Chimera/ChimeraX", "Napari", "None"],
        "widget_type": ToggleButtons,
        "tooltip": (
            "Application to use for manual mask creation. If 'None' is "
            "selected, user has to create a 'mask_base.mrc' file under the job "
            "directory by themselves using external applications, scp, etc."
        ),
        "group": "I/O",
    },
]
_OTHER_BINNING = Annotated[
    list[float],
    {
        "label": "Also create masks with this binning(s)",
        "tooltip": ("Create additional masks with the specified binning(s). "),
        "group": "I/O",
    },
]
_PRE_LOWPASS = Annotated[
    float | None,
    {
        "label": "Pre lowpass filter (A)",
        "tooltip": (
            "Apply a lowpass filter to the input volume before sending to the "
            "application. Filtered map will be created in the job directory."
        ),
        "group": "Volume",
    },
]
_DILATE_PIXELS = Annotated[
    int,
    {
        "label": "Dilate mask by (pixels)",
        "tooltip": (
            "Number of pixels to dilate the mask_base.mrc before applying the "
            "soft edge. Set to a negative value to erode the mask instead."
        ),
        "group": "Blurring",
    },
]
_SOFT_EDGE = Annotated[
    float,
    {
        "label": "Soft edge scale (A)",
        "tooltip": (
            "Scale of the soft edge in Angstrom. Mask density will be 0.5 at "
            "this distance from the mask boundary."
        ),
        "group": "Blurring",
    },
]
_BLUR_METHOD = Annotated[
    str,
    {
        "label": "Soft edge method",
        "choices": ["Cosine", "Gaussian"],
        "widget_type": ToggleButtons,
        "tooltip": (
            "Method to apply the soft edge. 'Cosine' will apply a cosine-"
            "shaped edge. 'Gaussian' will apply a Gaussian-shaped edge."
        ),
        "group": "Blurring",
    },
]
_THRESHOLD = Annotated[
    float,
    {
        "label": "Mask threshold",
        "tooltip": "Threshold that will be applied to the mask_base.mrc.",
        "group": "Blurring",
    },
]


class ManualMaskCreation(RelionExternalJob):
    """Manually create a mask from a volume using external apps."""

    _max_wait_time_sec = 24 * 3600  # 24 hours

    def output_nodes(self):
        return [("mask.mrc", "Mask3D.mrc")]

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5:{cls.__name__}"

    @classmethod
    def job_title(cls):
        return "Draw Mask"

    @classmethod
    def menu_id(cls):
        return MenuId.RELION_UTILS_JOB

    def run(
        self,
        in_3dref: MAP_TYPE = "",
        use_app: _USE_APP = "None",
        other_binning: _OTHER_BINNING = [],
        pre_lowpass: _PRE_LOWPASS = None,
        dilate_pixels: _DILATE_PIXELS = 1,
        soft_edge: _SOFT_EDGE = 8,  # A
        blur_method: _BLUR_METHOD = "Cosine",
        threshold: _THRESHOLD = 0.5,
    ):
        yield from _create_mask(
            self,
            in_3dref=in_3dref,
            use_app=use_app,
            other_binning=other_binning,
            pre_lowpass=pre_lowpass,
            dilate_pixels=dilate_pixels,
            soft_edge=soft_edge,
            blur_method=blur_method,
            threshold=threshold,
            max_wait_time_sec=self._max_wait_time_sec,
        )

    def provide_widget(self, job_dir):
        return QMaskCreateViewer(job_dir)


class ManualMaskCreationContinue(RelionExternalContinue):
    """Continue editing the mask, starting from the saved mask_base.mrc."""

    original_class = ManualMaskCreation

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5:{cls.__name__}"

    def run(
        self,
        in_3dref: MAP_TYPE = "",
        use_app: _USE_APP = "None",
        other_binning: _OTHER_BINNING = [],
        pre_lowpass: _PRE_LOWPASS = None,
        dilate_pixels: _DILATE_PIXELS = 1,
        soft_edge: _SOFT_EDGE = 8,  # A
        blur_method: _BLUR_METHOD = "Cosine",
        threshold: _THRESHOLD = 0.5,
    ):
        yield from _create_mask(
            self,
            in_3dref=in_3dref,
            use_app=use_app,
            other_binning=other_binning,
            pre_lowpass=pre_lowpass,
            dilate_pixels=dilate_pixels,
            soft_edge=soft_edge,
            blur_method=blur_method,
            threshold=threshold,
            max_wait_time_sec=ManualMaskCreation._max_wait_time_sec,
            continued=True,
        )


def _create_mask(
    job: RelionExternalJob,
    in_3dref: str,
    use_app: str,
    other_binning: list[float],
    pre_lowpass: float | None,
    dilate_pixels: int,
    soft_edge: float,
    blur_method: str,
    threshold: float,
    max_wait_time_sec: float,
    continued: bool = False,
):
    """Wait for the user to create (or update, if `continued`) the mask."""
    from scipy import ndimage as ndi

    out_job_dir = job.output_job_dir
    mask_path = out_job_dir.path / "mask.mrc"
    mask_base_path = out_job_dir.path / "mask_base.mrc"
    if blur_method == "Cosine":
        fn_blur = _blur_cos
    elif blur_method == "Gaussian":
        fn_blur = _blur_gaussian
    else:
        raise ValueError(f"Unknown blur method: {blur_method}")

    other_binning = list(other_binning)
    for other_bin in other_binning:
        if other_bin <= 0:
            raise ValueError(f"Invalid binning: {other_bin}")

    if pre_lowpass is not None and pre_lowpass > 0:
        with mrcfile.open(out_job_dir.resolve_path(in_3dref)) as mrc:
            img = mrc.data
            img_scale = mrc.voxel_size.x
        cutoff_rel = img_scale / pre_lowpass
        img = lowpass_filter(img, cutoff_rel)
        input_path = (out_job_dir.path / "map_filtered.mrc").as_posix()
        # the filtered map already exists if the job is continued
        with mrcfile.new(input_path, overwrite=True) as mrc:
            mrc.set_data(img.astype(np.float32))
            mrc.voxel_size = img_scale
    else:
        input_path = out_job_dir.resolve_path(in_3dref).as_posix()

    # A new job waits for the masks to be created. A continued job waits for them
    # to be overwritten, starting from the existing mask_base.mrc.
    initial_mask: Path | None = None
    if continued:
        stamp_mask, stamp_mask_base = file_stamp(mask_path), file_stamp(mask_base_path)
        if mask_base_path.exists():
            initial_mask = mask_base_path
            job.console.log("Waiting for user to update the mask_base.mrc.")
        else:
            job.console.log("mask_base.mrc not found. Starting from no mask.")
    else:
        stamp_mask = stamp_mask_base = None
        job.console.log("Waiting for user to create mask.")
    time_0 = time.time()

    env = os.environ.copy()
    env.pop("QT_API", None)

    # volume onesmask #1.1 on_grid #1
    if use_app == "Chimera/ChimeraX":
        if (chimerax := _find_chimera_exec()) is None:
            raise FileNotFoundError(
                "Neither ChimeraX nor Chimera executable found in PATH."
            )
        args = [chimerax, input_path]
        if initial_mask is not None:
            args.append(initial_mask.as_posix())
        popen_detached(
            args,
            cwd=out_job_dir.path,
            start_new_session=True,  # open in a new terminal on Linux
            env=env,
        )
    elif use_app == "Napari":
        python_exe = relion_python_executable()
        script_path = (
            Path(__file__).parent.parent / "scripts" / "mask_creation_napari.py"
        )
        args = [
            python_exe,
            script_path.as_posix(),
            input_path,
            out_job_dir.path.as_posix(),
            "--threshold",
            str(threshold),
        ]
        if initial_mask is not None:
            args += ["--mask", initial_mask.as_posix()]
        popen_detached(
            args,
            cwd=out_job_dir.path,
            start_new_session=True,  # open in a new terminal on Linux
            env=env,
        )
    # wait for user to create mask
    while not (
        is_file_updated(mask_path, stamp_mask)
        or is_file_updated(mask_base_path, stamp_mask_base)
    ):
        time.sleep(1)
        yield
        if time.time() - time_0 > max_wait_time_sec:
            job.console.log("Mask creation timed out.")
            raise TimeoutError("Mask creation timed out.")
    blurred_mask = None
    if is_file_updated(mask_base_path, stamp_mask_base):
        job.console.log("mask_base.mrc found. Applying soft edge.")
        time.sleep(1)  # make sure that the file is fully writtencp
        with mrcfile.open(mask_base_path) as mrc:
            mask_data = mrc.data
            scale = mrc.voxel_size.x
        mask_data = mask_data > threshold
        if dilate_pixels > 0:
            mask_data = ndi.binary_dilation(mask_data, _make_footprint(dilate_pixels))
        elif dilate_pixels < 0:
            mask_data = ndi.binary_erosion(mask_data, _make_footprint(-dilate_pixels))
        dist = ndi.distance_transform_edt(~mask_data)
        dist_scaled = dist / (soft_edge / scale)

        blurred_mask = fn_blur(dist_scaled)
        with mrcfile.new(mask_path, overwrite=True) as mrc:
            mrc.set_data(blurred_mask)
            mrc.voxel_size = (scale, scale, scale)
    if not mask_path.exists():
        raise ValueError(
            "Output mask not found. Please save the mask base as 'mask_base.mrc' "
            "under the job directory and try again."
        )
    if blurred_mask is None and other_binning:
        # mask.mrc is given by the user
        with mrcfile.open(mask_path) as mrc:
            blurred_mask = np.asarray(mrc.data, dtype=np.float32)
            scale = mrc.voxel_size.x
    for b in other_binning:
        mask_scaled_path = out_job_dir.path / f"mask_bin{b}.mrc"
        with mrcfile.new(mask_scaled_path, overwrite=True) as mrc:
            zoom = 1 / b
            mask_zoomed = ndi.zoom(blurred_mask, zoom, order=3)
            mask_zoomed = np.clip(mask_zoomed, 0.0, 1.0, dtype=np.float32)
            mrc.set_data(mask_zoomed)
            mrc.voxel_size = (scale * b, scale * b, scale * b)


def _make_footprint(radius: float):
    size = int(np.ceil(radius) * 2) + 1
    zz, yy, xx = np.indices((size, size, size), dtype=np.float32)
    center = size // 2
    distances = np.sqrt((zz - center) ** 2 + (yy - center) ** 2 + (xx - center) ** 2)
    return distances <= radius


def _blur_cos(dist_scaled):
    return (
        np.cos(np.clip(dist_scaled * np.pi / 2, 0, np.pi)).astype(np.float32) + 1
    ) / 2


def _blur_gaussian(dist_scaled):
    sigma = 1.0 / np.sqrt(2 * np.log(2))
    return np.exp(-(dist_scaled**2) / (2 * sigma**2), dtype=np.float32).astype(
        np.float32
    )


def _find_chimera_exec() -> str | None:
    if not (chimerax := shutil.which("chimerax")):
        if not (chimerax := shutil.which("chimera")):
            return None
    return chimerax


connect_jobs(
    _spa.Refine3DJob,
    ManualMaskCreation,
    node_mapping={"run_class001.mrc": "in_3dref"},
)

connect_jobs(
    ManualMaskCreation,
    _spa.PostProcessJob,
    node_mapping={
        mask_create_search_halfmap: "fn_in",
        "mask.mrc": "fn_mask",
    },
)
