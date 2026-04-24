from pathlib import Path
from typing import Annotated, Any

import mrcfile
import numpy as np
from starfile_rs import read_star, as_star
import polars as pl
from himena_relion._job_class import connect_jobs
from himena_relion.consts import MenuId
from himena_relion.external import RelionExternalJob
from himena_relion.relion5_tomo._builtins import (
    CtfEstimationTomoJob,
    AlignTiltSeriesImodFiducial,
    AlignTiltSeriesImodPatch,
    AlignTiltSeriesAreTomo2,
)
from himena_relion._annotated.io import IN_TILT
from .widgets import QAutoExcludeTiltsViewer

OUTPUT_FILE_NAME = "selected_tilt_series.star"


class AutoExcludeTiltImages(RelionExternalJob):
    """Automatically exclude bad tilt images based on the results of motion-correction
    and CTF estimation jobs."""

    def output_nodes(self):
        return [(OUTPUT_FILE_NAME, "TomogramGroupMetadata.star")]

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5_tomo:{cls.__name__}"

    @classmethod
    def job_title(cls):
        return "Auto Exclude Tilt Images"

    @classmethod
    def menu_id(cls):
        return MenuId.RELION_TILT_ALIGN_JOB

    @classmethod
    def job_is_tomo(cls):
        return True

    def run(
        self,
        in_mics: IN_TILT = "",
        dark_pixel_percentage: Annotated[
            float,
            {
                "label": "Exclude mics with dark pixels more than (%)",
                "min": 0.0,
                "max": 100.0,
                "tooltip": (
                    "If the percentage of dark pixels exceeds this threshold, the tilt "
                    "image will be excluded. Dark pixels are defined by the threshold "
                    "below. This filter is useful to exclude high-tilt micrographs "
                    "in which field of view was covered by the grid bars.\n"
                    "Set this to 0 to disable this filter."
                ),
                "group": "Threshold",
            },
        ] = 25.0,
        dark_pixel_value: Annotated[
            float,
            {
                "label": "Dark pixel threshold (A)",
                "min": -10000.0,
                "max": 10000.0,
                "tooltip": (
                    "Pixels with intensity less than or equal to this value will be "
                    "considered dark."
                ),
                "group": "Threshold",
            },
        ] = 0.0,
        max_defocus_deviation: Annotated[
            float,
            {
                "label": "Exclude defocus deviation more than (μm)",
                "min": 0.0,
                "tooltip": (
                    "If the deviation between the nominal defocus and the fitted "
                    "defocus (output of ctffind4) exceeds this threshold, the tilt "
                    "image will be excluded."
                ),
                "group": "Threshold",
            },
        ] = 10.0,
        max_motion: Annotated[
            float,
            {
                "label": "Exclude accumulated motion more than (A)",
                "min": 0.0,
                "tooltip": (
                    "If the accumulated motion (output of motion correction) exceeds "
                    "this threshold, the tilt image will be excluded."
                ),
                "group": "Threshold",
            },
        ] = 50.0,
        max_ice_ring_density: Annotated[
            float,
            {
                "label": "Exclude ice ring density more than",
                "min": 0.0,
                "tooltip": (
                    "If the ice ring density (output of ctffind4) exceeds this "
                    "threshold, the tilt image will be excluded."
                ),
                "group": "Threshold",
            },
        ] = 4.0,
    ):
        out_job_dir = self.output_job_dir
        in_mics = out_job_dir.resolve_path(in_mics)
        df_tilt = read_star(in_mics).first().trust_loop().to_polars()
        rln_dir = out_job_dir.relion_project_dir

        tilt_save_dir = out_job_dir.path / "tilt_series"
        tilt_save_dir.mkdir(exist_ok=True, parents=True)

        row_excluded: list[dict[str, Any]] = []

        for ts_star_path in df_tilt["rlnTomoTiltSeriesStarFile"]:
            ts_star_path_abs = out_job_dir.resolve_path(ts_star_path)
            loop = read_star(ts_star_path_abs).first().trust_loop().to_polars()
            indices: list[int] = []
            for ith, row in enumerate(loop.iter_rows(named=True)):
                if (
                    _defocus_ok(row, max_defocus_deviation)
                    and row.get("rlnAccumMotionTotal", 0.0) <= max_motion
                    and row.get("rlnCtfIceRingDensity", 0.0) <= max_ice_ring_density
                    and _dark_pixel_ok(
                        row, dark_pixel_value, dark_pixel_percentage, rln_dir
                    )
                ):
                    indices.append(ith)
                else:
                    row_excluded.append(row)
                yield
            loop_filt = loop[indices]
            tilt_save_dir_path = tilt_save_dir / Path(ts_star_path).name
            self.console.log(
                f"{loop.height - len(indices)}/{loop.height} tilt images excluded."
            )
            star_out = as_star({tilt_save_dir_path.stem: loop_filt})
            star_out.write(tilt_save_dir_path)
            yield

        output_node_path = out_job_dir.path / OUTPUT_FILE_NAME
        output_excluded_path = out_job_dir.path / "excluded_tilts.star"
        df_tilt_out = df_tilt.with_columns(
            pl.col("rlnTomoTiltSeriesStarFile")
            .map_elements(lambda p: str(tilt_save_dir / Path(p).name))
            .alias("rlnTomoTiltSeriesStarFile")
        )
        as_star({"global": df_tilt_out}).write(output_node_path)
        as_star({"excluded": pl.DataFrame(row_excluded)}).write(output_excluded_path)
        self.console.log(
            f"Auto-exclude tilt images finished successfully, output saved to "
            f"{output_node_path}"
        )

    def provide_widget(self, job_dir):
        return QAutoExcludeTiltsViewer(job_dir)


def _defocus_ok(row: dict[str, Any], thresh: float) -> bool:
    if "rlnTomoNominalDefocus" in row and "rlnDefocusU" in row and "rlnDefocusV" in row:
        nom = abs(row["rlnTomoNominalDefocus"])
        # convert from A to um
        uv_mean = (row["rlnDefocusU"] + row["rlnDefocusV"]) / 20000
        return abs(nom - uv_mean) <= thresh
    else:
        return True


def _dark_pixel_ok(
    row: dict[str, Any],
    value: float,
    percentage: float,
    relion_project_dir: Path,
) -> bool:
    if percentage == 0:
        return True
    path = relion_project_dir / str(row["rlnMicrographName"])
    if not path.exists():
        return True
    with mrcfile.open(path) as mrc:
        img = np.asarray(mrc.data)
    return np.sum(img <= value) <= percentage / 100 * img.size


connect_jobs(
    CtfEstimationTomoJob,
    AutoExcludeTiltImages,
    node_mapping={"tilt_series_ctf.star": "in_mics"},
)
for job_cls in [
    AlignTiltSeriesImodFiducial,
    AlignTiltSeriesImodPatch,
    AlignTiltSeriesAreTomo2,
]:
    connect_jobs(
        AutoExcludeTiltImages,
        job_cls,
        node_mapping={OUTPUT_FILE_NAME: "in_tiltseries"},
    )
