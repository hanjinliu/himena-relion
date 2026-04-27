from pathlib import Path
from typing import Any

import mrcfile
import numpy as np
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

        unique_optics_groups = dict[str, dict[str, Any]]()
        rows: list[dict[str, Any]] = []
        tomo_name_to_scale_map: dict[str, float] = {}
        tomo_name_to_size_x_map: dict[str, int] = {}
        tomo_name_to_size_y_map: dict[str, int] = {}
        tomo_name_to_size_z_map: dict[str, int] = {}
        tomo_name_to_optics_group_map: dict[str, int] = {}

        for tomo_meta in tsg_model.zip():
            if tomo_meta.optics_group_name not in unique_optics_groups:
                row = {
                    "rlnOpticsGroupName": tomo_meta.optics_group_name,
                    "rlnOpticsGroup": len(unique_optics_groups) + 1,
                    "rlnMtfFileName": "",
                    "rlnMicrographOriginalPixelSize": tomo_meta.original_pixel_size,
                    "rlnVoltage": tomo_meta.voltage,
                    "rlnSphericalAberration": tomo_meta.cs,
                    "rlnAmplitudeContrast": tomo_meta.amplitude_contrast,
                    "rlnMicrographPixelSize": tomo_meta.tomo_tilt_series_pixel_size,
                }
                rows.append(row)
                unique_optics_groups[tomo_meta.optics_group_name] = row
            else:
                row = unique_optics_groups[tomo_meta.optics_group_name]

            tomo_name_to_scale_map[tomo_meta.tomo_name] = (
                tomo_meta.tomo_tilt_series_pixel_size
            )
            tomo_name_to_size_x_map[tomo_meta.tomo_name] = tomo_meta.size_x
            tomo_name_to_size_y_map[tomo_meta.tomo_name] = tomo_meta.size_y
            tomo_name_to_size_z_map[tomo_meta.tomo_name] = tomo_meta.size_z
            tomo_name_to_optics_group_map[tomo_meta.tomo_name] = row["rlnOpticsGroup"]

        # e.g. TS_01 -> TS_01_000_corrected.mrc
        tomo_name_to_mic_name_map: dict[str, str] = {}
        tomo_name_to_mtx_map: dict[str, np.ndarray] = {}
        tomo_name_to_tilt_shape_map: dict[str, tuple[int, int]] = {}
        dfs: list[pl.DataFrame] = []
        optics: list[int] = []
        for star_path in tsg_model.tomo_tilt_series_star_file:
            ts_model = TSModel.validate_file(rln_dir / star_path)
            tomo_name = Path(star_path).stem
            idx = ts_model.nominal_stage_tilt_angle.abs().arg_min()
            if idx is not None:
                dfs.append(ts_model.dataframe[idx])
                optics.append(tomo_name_to_optics_group_map[tomo_name])
                mic_path = ts_model.micrograph_name[idx]
                tomo_name_to_mic_name_map[tomo_name] = mic_path
                with mrcfile.open(rln_dir / mic_path, header_only=True) as mrc:
                    tilt_shape_xy = (mrc.header.nx, mrc.header.ny)
                tomo_name_to_mtx_map[tomo_name] = ts_model.prep_matrix(
                    idx,
                    (
                        tomo_name_to_size_x_map[tomo_name],
                        tomo_name_to_size_y_map[tomo_name],
                        tomo_name_to_size_z_map[tomo_name],
                    ),
                    tilt_shape_xy=tilt_shape_xy,
                    pixel_size=tomo_name_to_scale_map[tomo_name],
                )
                tomo_name_to_tilt_shape_map[tomo_name] = tilt_shape_xy

        df_micrographs = pl.concat(dfs, how="vertical_relaxed").with_columns(
            pl.Series("rlnOpticsGroup", optics)
        )
        df_optics = pl.DataFrame(rows)
        mic_star_spa = as_star({"optics": df_optics, "micrographs": df_micrographs})
        mic_star_spa.write(self.output_job_dir.path / "micrographs.star")

        _tomo_name = pl.col("rlnTomoName")
        _tomo_scale = _tomo_name.replace_strict(
            tomo_name_to_scale_map, return_dtype=pl.Float32
        )
        _tomo_size_x = _tomo_name.replace_strict(
            tomo_name_to_size_x_map, return_dtype=pl.Float32
        )
        _tomo_size_y = _tomo_name.replace_strict(
            tomo_name_to_size_y_map, return_dtype=pl.Float32
        )
        _tomo_size_z = _tomo_name.replace_strict(
            tomo_name_to_size_z_map, return_dtype=pl.Float32
        )

        df_parts = ptcl_model.particles.dataframe.with_columns(
            _tomo_name.replace(tomo_name_to_mic_name_map).alias("rlnMicrographName"),
            pl.col("rlnCenteredCoordinateXAngst")
            .truediv(_tomo_scale)
            .add(_tomo_size_x / 2)
            .alias("rlnCoordinateX"),
            pl.col("rlnCenteredCoordinateYAngst")
            .truediv(_tomo_scale)
            .add(_tomo_size_y / 2)
            .alias("rlnCoordinateY"),
            pl.col("rlnCenteredCoordinateZAngst")
            .truediv(_tomo_scale)
            .add(_tomo_size_z / 2)
            .alias("rlnCoordinateZ"),
            pl.col("rlnTomoName")
            .replace_strict(tomo_name_to_optics_group_map, return_dtype=pl.Int32)
            .alias("rlnOpticsGroup"),
        )
        subs: list[pl.DataFrame] = []
        for (tomo_name,), sub in df_parts.group_by("rlnTomoName"):
            mtx = tomo_name_to_mtx_map[tomo_name]
            scale = tomo_name_to_scale_map[tomo_name]
            xyz = _get_xyz(sub, scale)
            xyz_transformed = (mtx @ np.hstack((xyz, np.ones((xyz.shape[0], 1)))).T).T[
                :, :3
            ]
            # xyz_transformed = (np.linalg.inv(mtx) @ np.hstack((xyz, np.ones((xyz.shape[0], 1)))).T).T[:, :3]
            sub = sub.with_columns(
                pl.Series("rlnCoordinateX", xyz_transformed[:, 0]),
                pl.Series("rlnCoordinateY", xyz_transformed[:, 1]),
            )
            tilt_xy_shape = tomo_name_to_tilt_shape_map[tomo_name]
            subs.append(
                sub.filter(
                    pl.col("rlnCoordinateX").is_between(0, tilt_xy_shape[0]),
                    pl.col("rlnCoordinateY").is_between(0, tilt_xy_shape[1]),
                )
            )
        df_parts = pl.concat(subs, how="vertical_relaxed")
        part_star_spa = as_star({"optics": df_optics, "particles": df_parts})
        part_star_spa.write(self.output_job_dir.path / "hybrid_data.star")


# Adapted from
# https://github.com/3dem/relion/blob/master/src/tomography_python_programs/view/particles.py
def _get_xyz(particle_df: pl.DataFrame, scale: float) -> np.ndarray:
    from scipy.spatial.transform import Rotation as R

    zyx = particle_df.select(
        "rlnCoordinateZ", "rlnCoordinateY", "rlnCoordinateX"
    ).to_numpy()

    # get particle shifts if present
    origin_headings = ["rlnOriginZAngst", "rlnOriginYAngst", "rlnOriginXAngst"]
    if all(heading in particle_df.columns for heading in origin_headings):
        origin_zyx = particle_df.select(origin_headings).to_numpy()
        origin_in_dataframe = True
    else:
        origin_in_dataframe = False

    # get the subtomogram orientation within the tomogram, if present
    subtomogram_orientation_headings = [
        "rlnTomoSubtomogramRot",
        "rlnTomoSubtomogramTilt",
        "rlnTomoSubtomogramPsi",
    ]
    if all(
        heading in particle_df.columns for heading in subtomogram_orientation_headings
    ):
        eulers = particle_df.select(subtomogram_orientation_headings).to_numpy()
        subtomogram_rotation = R.from_euler(
            seq="ZYZ", angles=eulers, degrees=True
        ).inv()
        subtomogram_orientation_in_dataframe = True
    else:
        subtomogram_orientation_in_dataframe = False

    # rotate the shifts if necessary
    if subtomogram_orientation_in_dataframe and origin_in_dataframe:
        origin_xyz = origin_zyx[:, ::-1]
        origin_xyz = subtomogram_rotation.apply(origin_xyz)
        origin_zyx = origin_xyz[:, ::-1]

    if origin_in_dataframe:
        zyx -= origin_zyx / scale
        # zyx -= origin_zyx / particle_df["rlnImagePixelSize"].to_numpy()
    return zyx[:, ::-1]
