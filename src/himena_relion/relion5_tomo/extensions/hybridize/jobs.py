from pathlib import Path
from typing import Any

import polars as pl
from starfile_rs import as_star
from himena_relion.consts import MenuId
from himena_relion.external import RelionExternalJob
from himena_relion.schemas import TomogramsGroupModel, TSModel, ParticleMetaModel
from himena_relion._annotated.io import IN_TILT, IN_PARTICLES


class TakeZeroTiltMicrographs(RelionExternalJob):
    def output_nodes(self):
        return [
            ("micrographs.star", "MicrographsData.star"),
            ("hybrid_data.star", "ParticlesData.star"),
        ]

    @classmethod
    def import_path(cls):
        return f"himena_relion.relion5_tomo:{cls.__name__}"

    @classmethod
    def job_title(cls):
        return "Take Zero-tilt Micrographs"

    @classmethod
    def menu_id(cls):
        return MenuId.RELION_PICK_JOB

    def run(
        self,
        in_mics: IN_TILT,  # path
        in_parts: IN_PARTICLES,  # path
    ):
        rln_dir = self.output_job_dir.relion_project_dir
        tsg_model = TomogramsGroupModel.validate_file(rln_dir / in_mics)
        ptcl_model = ParticleMetaModel.validate_file(rln_dir / in_parts)

        unique_optics_groups = set[str]()
        rows: list[dict[str, Any]] = []
        tomo_name_to_scale_map: dict[str, float] = {}
        tomo_name_to_size_x_map: dict[str, int] = {}
        tomo_name_to_size_y_map: dict[str, int] = {}

        for tomo_meta in tsg_model.zip():
            unique_optics_groups.add(tomo_meta.optics_group_name)
            row = {
                "rlnOpticsGroupName": tomo_meta.optics_group_name,
                "rlnOpticsGroup": len(unique_optics_groups),
                "rlnMtfFileName": "",
                "rlnMicrographOriginalPixelSize": tomo_meta.original_pixel_size,
                "rlnVoltage": tomo_meta.voltage,
                "rlnSphericalAberration": tomo_meta.cs,
                "rlnAmplitudeContrast": tomo_meta.amplitude_contrast,
                "rlnMicrographPixelSize": tomo_meta.tomo_tilt_series_pixel_size,
            }
            rows.append(row)
            tomo_name_to_scale_map[tomo_meta.tomo_name] = (
                tomo_meta.tomo_tilt_series_pixel_size
            )
            tomo_name_to_size_x_map[tomo_meta.tomo_name] = tomo_meta.size_x
            tomo_name_to_size_y_map[tomo_meta.tomo_name] = tomo_meta.size_y

        # e.g. TS_01 -> TS_01_000_corrected.mrc
        tomo_name_to_mic_name_map: dict[str, str] = {}
        dfs = []
        for star_path in tsg_model.tomo_tilt_series_star_file:
            ts_model = TSModel.validate_file(rln_dir / star_path)
            index_argmin = ts_model.nominal_stage_tilt_angle.arg_min()
            if index_argmin is not None:
                dfs.append(ts_model.dataframe[index_argmin])
                ts_model.micrograph_name[index_argmin]
                tomo_name_to_mic_name_map[Path(star_path).stem] = (
                    ts_model.micrograph_name[index_argmin]
                )
        df_micrographs = pl.concat(dfs, how="vertical_relaxed")
        df_optics = pl.DataFrame(rows)
        mic_star_spa = as_star({"optics": df_optics, "micrographs": df_micrographs})
        mic_star_spa.write(self.output_job_dir.path / "micrographs.star")

        _tomo_scale = pl.col("rlnTomoName").replace_strict(
            tomo_name_to_scale_map, return_dtype=pl.Float32
        )
        _tomo_center_x = (
            pl.col("rlnTomoName").replace_strict(
                tomo_name_to_size_x_map, return_dtype=pl.Float32
            )
            / 2
        )
        _tomo_center_y = (
            pl.col("rlnTomoName").replace_strict(
                tomo_name_to_size_y_map, return_dtype=pl.Float32
            )
            / 2
        )
        df_parts = ptcl_model.particles.dataframe.with_columns(
            pl.col("rlnTomoName")
            .replace(tomo_name_to_mic_name_map)
            .alias("rlnMicrographName"),
            pl.col("rlnCenteredCoordinateXAngst")
            .truediv(_tomo_scale)
            .add(_tomo_center_x)
            .alias("rlnCoordinateX"),
            pl.col("rlnCenteredCoordinateYAngst")
            .truediv(_tomo_scale)
            .add(_tomo_center_y)
            .alias("rlnCoordinateY"),
        )

        part_star_spa = as_star({"optics": df_optics, "particles": df_parts})
        part_star_spa.write(self.output_job_dir.path / "hybrid_data.star")
