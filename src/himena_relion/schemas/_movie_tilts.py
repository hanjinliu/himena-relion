from pathlib import Path
import starfile_rs.schema.pandas as schema


class OpticsModel(schema.LoopDataModel):
    optics_group_name: schema.Series[str] = schema.Field("rlnOpticsGroupName")
    optics_group: schema.Series[int] = schema.Field("rlnOpticsGroup")
    mtf_file_name: schema.Series[str] = schema.Field("rlnMtfFileName", default=None)
    mic_orig_pixel_size: schema.Series[float] = schema.Field(
        "rlnMicrographOriginalPixelSize", default=None
    )
    voltage: schema.Series[float] = schema.Field("rlnVoltage", default=None)
    cs: schema.Series[float] = schema.Field("rlnSphericalAberration", default=None)
    amplitude_contrast: schema.Series[float] = schema.Field(
        "rlnAmplitudeContrast", default=None
    )

    def make_optics_map(self) -> dict[int, "SingleOpticsModel"]:
        """Create a mapping from optics group ID to SingleOpticsModel."""
        optics_map = {}
        for i in range(len(self.optics_group)):
            key = self.optics_group[i]
            optics = SingleOpticsModel(
                optics_group_name=self.optics_group_name[i],
                optics_group=key,
                mtf_file_name=_ith_or_none(self.mtf_file_name, i),
                mic_orig_pixel_size=_ith_or_none(self.mic_orig_pixel_size, i),
                voltage=_ith_or_none(self.voltage, i),
                cs=_ith_or_none(self.cs, i),
                amplitude_contrast=_ith_or_none(self.amplitude_contrast, i),
            )
            optics_map[key] = optics
        return optics_map


def _ith_or_none(series: schema.Series | None, i: int):
    if series is None:
        return None
    return series[i]


class SingleOpticsModel(schema.SingleDataModel):
    optics_group_name: str = schema.Field("rlnOpticsGroupName")
    optics_group: int = schema.Field("rlnOpticsGroup")
    mtf_file_name: str = schema.Field("rlnMtfFileName", default="")
    mic_orig_pixel_size: float = schema.Field(
        "rlnMicrographOriginalPixelSize", default=None
    )
    voltage: float = schema.Field("rlnVoltage", default=300.0)
    cs: float = schema.Field("rlnSphericalAberration", default=2.7)
    amplitude_contrast: float = schema.Field("rlnAmplitudeContrast", default=0.1)
    mc_pixel_size: float = schema.Field("rlnMicrographMoviePixelSize", default=None)


class MoviesModel(schema.LoopDataModel):
    movie_name: schema.Series[str] = schema.Field("rlnMicrographMovieName")
    """Path to the movie file."""
    optics_group: schema.Series[int] = schema.Field("rlnOpticsGroup")


class MoviesStarModel(schema.StarModel):
    """movies.star file content."""

    optics: OpticsModel = schema.Field()
    movies: MoviesModel = schema.Field()


class MicrographsModel(schema.LoopDataModel):
    mic_name: schema.Series[str] = schema.Field("rlnMicrographName")
    """Path to the micrograph file."""
    optics_group: schema.Series[int] = schema.Field("rlnOpticsGroup")
    ctf_image: schema.Series[str] = schema.Field("rlnCtfImage", default=None)


class MicrographGroupMetaModel(schema.StarModel):
    optics: SingleOpticsModel = schema.Field()
    micrographs: MicrographsModel = schema.Field()


class TSModel(schema.LoopDataModel):
    """Star file content such as TS_01.star"""

    movie_name: schema.Series[str] = schema.Field("rlnMicrographMovieName")
    frame_count: schema.Series[int] = schema.Field("rlnTomoTiltMovieFrameCount")
    nominal_stage_tilt_angle: schema.Series[float] = schema.Field(
        "rlnTomoNominalStageTiltAngle"
    )
    nominal_tilt_axis_angle: schema.Series[float] = schema.Field(
        "rlnTomoNominalTiltAxisAngle"
    )
    pre_exposure: schema.Series[float] = schema.Field("rlnMicrographPreExposure")
    nominal_defocus: schema.Series[float] = schema.Field("rlnTomoNominalDefocus")
    micrograph_name: schema.Series[str] = schema.Field(
        "rlnMicrographName", default=None
    )
    micrograph_movie_name: schema.Series[str] = schema.Field(
        "rlnMicrographMovieName", default=None
    )
    ctf_image: schema.Series[str] = schema.Field("rlnCtfImage", default=None)

    def ts_paths_sorted(self, rln_dir: Path) -> list[Path]:
        order = self.nominal_stage_tilt_angle.argsort()
        paths = [rln_dir / p for p in self.micrograph_name]
        return [paths[i] for i in order]

    def ts_movie_paths_sorted(self) -> list[Path]:
        order = self.nominal_stage_tilt_angle.argsort()
        paths = [p for p in self.movie_name]
        return [paths[i] for i in order]


class TSAlignModel(schema.LoopDataModel):
    xtilt: schema.Series[float] = schema.Field("rlnTomoXTilt")  # 21
    ytilt: schema.Series[float] = schema.Field("rlnTomoYTilt")  # 22
    zrot: schema.Series[float] = schema.Field("rlnTomoZRot")  # 23
    xshift: schema.Series[float] = schema.Field("rlnTomoXShiftAngst")  # 24
    yshift: schema.Series[float] = schema.Field("rlnTomoYShiftAngst")  # 25


class TSGroupModel(schema.LoopDataModel):
    """Star file content such as TomogramsGroup.star"""

    tomo_name: schema.Series[str] = schema.Field("rlnTomoName")
    tomo_tilt_series_star_file: schema.Series[str] = schema.Field(
        "rlnTomoTiltSeriesStarFile"
    )
    voltage: schema.Series[float] = schema.Field("rlnVoltage")
    cs: schema.Series[float] = schema.Field("rlnSphericalAberration")
    amplitude_contrast: schema.Series[float] = schema.Field("rlnAmplitudeContrast")
    original_pixel_size: schema.Series[float] = schema.Field(
        "rlnMicrographOriginalPixelSize"
    )
    tomo_hand: schema.Series[int] = schema.Field("rlnTomoHand")


class TomogramsGroupModel(schema.LoopDataModel):
    """Star file content such as TomogramsGroup.star"""

    tomo_name: schema.Series[str] = schema.Field("rlnTomoName")
    voltage: schema.Series[float] = schema.Field("rlnVoltage")
    cs: schema.Series[float] = schema.Field("rlnSphericalAberration")
    amplitude_contrast: schema.Series[float] = schema.Field("rlnAmplitudeContrast")
    original_pixel_size: schema.Series[float] = schema.Field(
        "rlnMicrographOriginalPixelSize"
    )
    tomo_hand: schema.Series[int] = schema.Field("rlnTomoHand")
    optics_group_name: schema.Series[str] = schema.Field("rlnOpticsGroupName")
    tomo_tilt_series_pixel_size: schema.Series[float] = schema.Field(
        "rlnTomoTiltSeriesPixelSize"
    )
    tomo_tilt_series_star_file: schema.Series[str] = schema.Field(
        "rlnTomoTiltSeriesStarFile"
    )
    etomo_directive_file: schema.Series[str] = schema.Field("rlnEtomoDirectiveFile")
    tomogram_binning: schema.Series[float] = schema.Field("rlnTomoTomogramBinning")
    size_x: schema.Series[int] = schema.Field("rlnTomoSizeX")
    size_y: schema.Series[int] = schema.Field("rlnTomoSizeY")
    size_z: schema.Series[int] = schema.Field("rlnTomoSizeZ")
