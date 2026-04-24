from pathlib import Path
from typing import Annotated, Any

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
# from .widgets import QInspectViewer

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
        max_defocus_deviation: Annotated[
            float,
            {
                "label": "Maximum defocus deviation (μm)",
                "min": 0.0,
                "tooltip": (
                    "If the deviation between the nominal defocus and the fitted "
                    "defocus (output of ctffind4) exceeds this threshold, the tilt "
                    "image will be excluded."
                ),
                "group": "I/O",
            },
        ] = 1.0,
        max_motion: Annotated[
            float,
            {
                "label": "Maximum accumulated motion (A)",
                "min": 0.0,
                "tooltip": (
                    "If the accumulated motion (output of motion correction) exceeds "
                    "this threshold, the tilt image will be excluded."
                ),
                "group": "I/O",
            },
        ] = 20.0,
        max_ice_ring_density: Annotated[
            float,
            {
                "label": "Maximum ice ring density (arbitrary units)",
                "min": 0.0,
                "tooltip": (
                    "If the ice ring density (output of ctffind4) exceeds this "
                    "threshold, the tilt image will be excluded."
                ),
                "group": "I/O",
            },
        ] = 4.0,
    ):
        df_tilt = read_star(in_mics).first().trust_loop().to_polars()
        out_job_dir = self.output_job_dir

        tilt_save_dir = out_job_dir.path / "tilt_series"
        tilt_save_dir.mkdir(exist_ok=True, parents=True)

        for ts_star_path in df_tilt["rlnTomoTiltSeriesStarFile"]:
            ts_star_path_abs = out_job_dir.resolve_path(ts_star_path)
            loop = read_star(ts_star_path_abs).first().trust_loop().to_polars()
            indices: list[int] = []
            for ith, row in enumerate(loop.iter_rows(named=True)):
                if (
                    _defocus_ok(row, max_defocus_deviation)
                    and row.get("rlnAccumMotionTotal", 0.0) <= max_motion
                    and row.get("rlnCtfIceRingDensity", 0.0) <= max_ice_ring_density
                ):
                    indices.append(ith)
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
        df_tilt_out = df_tilt.with_columns(
            pl.col("rlnTomoTiltSeriesStarFile")
            .map_elements(lambda p: str(tilt_save_dir / Path(p).name))
            .alias("rlnTomoTiltSeriesStarFile")
        )
        as_star({"global": df_tilt_out}).write(output_node_path)
        self.console.log(
            f"Auto-exclude tilt images finished successfully, output saved to "
            f"{output_node_path}"
        )


def _defocus_ok(row: dict[str, Any], thresh: float) -> bool:
    if "rlnTomoNominalDefocus" in row and "rlnDefocusU" in row and "rlnDefocusV" in row:
        nom = abs(row["rlnTomoNominalDefocus"])
        uv_mean = (
            row["rlnDefocusU"] + row["rlnDefocusV"]
        ) / 20000  # convert from A to um
        return abs(nom - uv_mean) <= thresh
    else:
        return True


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
