from pathlib import Path
import subprocess
import time
import os
import shutil
from typing import Annotated

import mrcfile
import numpy as np

from himena.qt.magicgui import ToggleButtons
from himena_relion._job_class import connect_jobs
from himena_relion.consts import MenuId
from himena_relion.external import RelionExternalJob
from himena_relion._utils import relion_python_executable
from himena_relion._annotated.io import MAP_TYPE
from himena_relion.relion5.extensions.volume_tools.widgets import QMaskCreateViewer
from himena_relion.relion5._connections import mask_create_search_halfmap
from himena_relion.relion5 import _builtins as _spa


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
        return "Manual Mask Creation"

    @classmethod
    def menu_id(cls):
        return MenuId.RELION_UTILS_JOB

    def run(
        self,
        in_3dref: MAP_TYPE = "",
        use_app: Annotated[
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
        ] = "None",
        dilate_pixels: Annotated[
            int,
            {
                "label": "Dilate mask by (pixels)",
                "tooltip": (
                    "Number of pixels to dilate the mask_base.mrc before applying the "
                    "soft edge. Set to a negative value to erode the mask instead."
                ),
                "group": "Blurring",
            },
        ] = 1,
        soft_edge: Annotated[
            float,
            {
                "label": "Soft edge scale (A)",
                "tooltip": (
                    "Scale of the soft edge in Angstrom. Mask density will be 0.5 at "
                    "this distance from the mask boundary."
                ),
                "group": "Blurring",
            },
        ] = 8,  # A
        blur_method: Annotated[
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
        ] = "Cosine",
        threshold: Annotated[
            float,
            {
                "label": "Mask threshold",
                "tooltip": "Threshold that will be applied to the mask_base.mrc.",
                "group": "Blurring",
            },
        ] = 0.5,
    ):
        from scipy import ndimage as ndi

        out_job_dir = self.output_job_dir
        mask_path = out_job_dir.path / "mask.mrc"
        mask_base_path = out_job_dir.path / "mask_base.mrc"
        if blur_method == "Cosine":
            fn_blur = _blur_cos
        elif blur_method == "Gaussian":
            fn_blur = _blur_gaussian
        else:
            raise ValueError(f"Unknown blur method: {blur_method}")

        input_path = out_job_dir.resolve_path(in_3dref).as_posix()
        time_0 = time.time()
        self.console.log("Waiting for user to create mask.")

        # volume onesmask #1.1 on_grid #1
        if use_app == "Chimera/ChimeraX":
            if (chimerax := _find_chimera_exec()) is None:
                raise FileNotFoundError(
                    "Neither ChimeraX nor Chimera executable found in PATH."
                )
            subprocess.run(
                [chimerax, input_path],
                cwd=out_job_dir.path,
            )
        elif use_app == "Napari":
            python_exe = relion_python_executable()
            script_path = (
                Path(__file__).parent.parent / "scripts" / "mask_creation_napari.py"
            )
            env = os.environ.copy()
            env.pop("QT_API", None)
            subprocess.run(
                [
                    python_exe,
                    script_path.as_posix(),
                    input_path,
                    out_job_dir.path.as_posix(),
                ],
                cwd=out_job_dir.path,
                env=env,
            )
        else:
            # wait for user to create mask by themselves
            while not mask_path.exists() and not mask_base_path.exists():
                time.sleep(1)
                yield
                if time.time() - time_0 > self._max_wait_time_sec:
                    self.console.log("Mask creation timed out.")
                    raise TimeoutError("Mask creation timed out.")
        if mask_base_path.exists():
            with mrcfile.open(mask_base_path) as mrc:
                mask_data = mrc.data
                scale = mrc.voxel_size.x
            mask_data = mask_data > threshold
            if dilate_pixels > 0:
                mask_data = ndi.binary_dilation(
                    mask_data, _make_footprint(dilate_pixels)
                )
            elif dilate_pixels < 0:
                mask_data = ndi.binary_erosion(
                    mask_data, _make_footprint(-dilate_pixels)
                )
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

    def provide_widget(self, job_dir):
        return QMaskCreateViewer(job_dir)


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
