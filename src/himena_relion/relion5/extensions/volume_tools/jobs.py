import subprocess
import time
from typing import Annotated

import mrcfile
import numpy as np

from himena.qt.magicgui import ToggleButtons
from himena_relion.consts import MenuId
from himena_relion.external import RelionExternalJob
from himena_relion._configs import get_chimera_exe
from himena_relion._annotated.io import MAP_TYPE
from himena_relion.relion5.extensions.volume_tools.widgets import QMaskCreateViewer


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
                "choices": ["Chimera/ChimeraX", "None"],
                "widget_type": ToggleButtons,
            },
        ] = "None",
        dilate_pixels: Annotated[
            int,
            {
                "label": "Dilate mask by (pixels)",
                "tooltip": (
                    "Number of pixels to dilate the mask_base.mrc before applying the "
                    "soft edge."
                ),
                "group": "Blurring",
            },
        ] = 1,
        soft_edge: Annotated[
            float,
            {
                "label": "Soft edge scale (A)",
                "group": "Blurring",
            },
        ] = 20,  # A
        blur_method: Annotated[
            str,
            {
                "label": "Soft edge method",
                "choices": ["Cosine", "Gaussian"],
                "widget_type": ToggleButtons,
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

        if blur_method == "Cosine":
            fn_blur = _blur_cos
        elif blur_method == "Gaussian":
            fn_blur = _blur_gaussian
        else:
            raise ValueError(f"Unknown blur method: {blur_method}")
        # volume onesmask #1.1 on_grid #1
        out_job_dir = self.output_job_dir
        input_path = out_job_dir.resolve_path(in_3dref).as_posix()
        if use_app == "Chimera/ChimeraX":
            chimerax = get_chimera_exe()
            subprocess.Popen(
                [chimerax, input_path],
                cwd=out_job_dir.path,
                start_new_session=True,
            )
        mask_path = out_job_dir.path / "mask.mrc"
        mask_base_path = out_job_dir.path / "mask_base.mrc"

        time_0 = time.time()
        self.console.log("Waiting for user to create mask.")
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
            mask_data = ndi.binary_dilation(mask_data, _make_footprint(dilate_pixels))
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
    return np.exp(-(dist_scaled**2) / 2, dtype=np.float32)
