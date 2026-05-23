from pathlib import Path
from typing import Iterator, NamedTuple
import numpy as np
import polars as pl
import starfile_rs.schema.polars as schema


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


class MoviesModel(schema.LoopDataModel):
    movie_name: schema.Series[str] = schema.Field("rlnMicrographMovieName")
    """Path to the movie file."""
    optics_group: schema.Series[int] = schema.Field("rlnOpticsGroup")


class MicrographsModel(schema.LoopDataModel):
    mic_name: schema.Series[str] = schema.Field("rlnMicrographName")
    """Path to the micrograph file."""
    optics_group: schema.Series[int] = schema.Field("rlnOpticsGroup")
    ctf_image: schema.Series[str] = schema.Field("rlnCtfImage", default=None)


class MoviesStarModel(schema.StarModel):
    """movies.star file content."""

    optics: OpticsModel = schema.Field()
    movies: MoviesModel = schema.Field()

    Optics = OpticsModel
    Movies = MoviesModel


class MicrographsStarModel(schema.StarModel):
    optics: OpticsModel = schema.Field()
    micrographs: MicrographsModel = schema.Field()

    Optics = OpticsModel
    Micrographs = MicrographsModel


class TSModel(schema.LoopDataModel):
    """Star file content such as TS_01.star"""

    movie_name: schema.Series[str] = schema.Field(
        "rlnMicrographMovieName", default=None
    )
    frame_count: schema.Series[int] = schema.Field(
        "rlnTomoTiltMovieFrameCount", default=None
    )
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
    micrograph_name_even: schema.Series[str] = schema.Field(
        "rlnMicrographNameEven", default=None
    )
    micrograph_name_odd: schema.Series[str] = schema.Field(
        "rlnMicrographNameOdd", default=None
    )
    ctf_image: schema.Series[str] = schema.Field("rlnCtfImage", default=None)

    tomo_xtilt: schema.Series[float] = schema.Field("rlnTomoXTilt", default=None)
    tomo_ytilt: schema.Series[float] = schema.Field("rlnTomoYTilt", default=None)
    tomo_zrot: schema.Series[float] = schema.Field("rlnTomoZRot", default=None)
    tomo_xshift_angst: schema.Series[float] = schema.Field(
        "rlnTomoXShiftAngst", default=None
    )
    tomo_yshift_angst: schema.Series[float] = schema.Field(
        "rlnTomoYShiftAngst", default=None
    )

    def ts_paths_sorted(self, rln_dir: Path | None = None) -> list[str]:
        order = self.nominal_stage_tilt_angle.arg_sort()
        if rln_dir is None:
            paths = list(self.micrograph_name)
        else:
            paths = [str(rln_dir / p) for p in self.micrograph_name]
        return [paths[i] for i in order]

    def ts_movie_paths_sorted(self) -> list[str]:
        order = self.nominal_stage_tilt_angle.arg_sort()
        paths = list(self.movie_name)
        return [paths[i] for i in order]

    def ts_even_odd_paths_sorted(self, rln_dir: Path) -> tuple[list[str], list[str]]:
        order = self.nominal_stage_tilt_angle.arg_sort()
        even_paths = list(self.micrograph_name_even)
        odd_paths = list(self.micrograph_name_odd)
        return (
            [str(rln_dir / even_paths[i]) for i in order],
            [str(rln_dir / odd_paths[i]) for i in order],
        )

    def need_rot90(self) -> bool:
        degree = self.nominal_tilt_axis_angle.mean()
        return abs((float(degree) + 90) % 180 - 90)

    def prep_matrix(
        self,
        index: int,
        tomo_shape_xyz: tuple[int, int, int],
        tilt_shape_xy: tuple[int, int],
        pixel_size: float,
    ):
        from scipy.spatial.transform import Rotation

        s0 = _as_translate_matrix(
            -tomo_shape_xyz[0] // 2,
            -tomo_shape_xyz[1] // 2,
            -tomo_shape_xyz[2] // 2,
        )
        r0 = _as_affine_matrix(
            Rotation.from_rotvec(
                [self.tomo_xtilt[index], 0, 0], degrees=True
            ).as_matrix()
        )
        r1 = _as_affine_matrix(
            Rotation.from_rotvec(
                [0, self.tomo_ytilt[index], 0], degrees=True
            ).as_matrix()
        )
        r2 = _as_affine_matrix(
            Rotation.from_rotvec(
                [0, 0, self.tomo_zrot[index]], degrees=True
            ).as_matrix()
        )
        s1 = _as_translate_matrix(
            self.tomo_xshift_angst[index] / pixel_size,
            self.tomo_yshift_angst[index] / pixel_size,
            0,
        )
        s2 = _as_translate_matrix(
            tilt_shape_xy[0] // 2,
            tilt_shape_xy[1] // 2,
            0,
        )
        transformations = s2 @ s1 @ r2 @ r1 @ r0 @ s0
        return transformations


def _as_translate_matrix(tx, ty, tz):
    out = np.eye(4, dtype=np.float32)
    out[:3, 3] = [tx, ty, tz]
    return out


def _as_affine_matrix(rot: np.ndarray):
    out = np.eye(4, dtype=np.float32)
    out[:3, :3] = rot
    return out


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
    tomo_hand: schema.Series[float] = schema.Field("rlnTomoHand")
    optics_group_name: schema.Series[str] = schema.Field(
        "rlnOpticsGroupName", default=None
    )
    tomo_tilt_series_pixel_size: schema.Series[float] = schema.Field(
        "rlnTomoTiltSeriesPixelSize",
        default=None,
    )
    etomo_directive_file: schema.Series[str] = schema.Field(
        "rlnEtomoDirectiveFile", default=None
    )

    def zip(self) -> Iterator["TSMeta"]:
        """Zip the fields into a list of tuples."""
        for val in zip(
            self.tomo_name,
            self.voltage,
            self.cs,
            self.amplitude_contrast,
            self.original_pixel_size,
            self.tomo_hand.cast(pl.Int32),
            self.optics_group_name
            if self.optics_group_name is not None
            else ["--"] * len(self.tomo_name),
            self.tomo_tilt_series_pixel_size
            if self.tomo_tilt_series_pixel_size is not None
            else self.original_pixel_size,
        ):
            yield TSMeta(*val)


class TSMeta(NamedTuple):
    tomo_name: str
    voltage: float
    cs: float
    amplitude_contrast: float
    original_pixel_size: float
    tomo_hand: int
    optics_group_name: str
    tomo_tilt_series_pixel_size: float


class TomoMeta(NamedTuple):
    tomo_name: str
    voltage: float
    cs: float
    amplitude_contrast: float
    original_pixel_size: float
    tomo_hand: int
    optics_group_name: str
    tomo_tilt_series_pixel_size: float
    tomogram_binning: float
    size_x: int
    size_y: int
    size_z: int


class TomogramsGroupModel(schema.LoopDataModel):
    """Star file content such as TomogramsGroup.star"""

    tomo_name: schema.Series[str] = schema.Field("rlnTomoName")
    voltage: schema.Series[float] = schema.Field("rlnVoltage")
    cs: schema.Series[float] = schema.Field("rlnSphericalAberration")
    amplitude_contrast: schema.Series[float] = schema.Field("rlnAmplitudeContrast")
    original_pixel_size: schema.Series[float] = schema.Field(
        "rlnMicrographOriginalPixelSize"
    )
    tomo_hand: schema.Series[float] = schema.Field("rlnTomoHand")
    optics_group_name: schema.Series[str] = schema.Field(
        "rlnOpticsGroupName", default=None
    )
    tomo_tilt_series_pixel_size: schema.Series[float] = schema.Field(
        "rlnTomoTiltSeriesPixelSize"
    )
    tomo_tilt_series_star_file: schema.Series[str] = schema.Field(
        "rlnTomoTiltSeriesStarFile"
    )
    # this is optional and not used yet
    # etomo_directive_file: schema.Series[str] = schema.Field("rlnEtomoDirectiveFile")
    tomogram_binning: schema.Series[float] = schema.Field("rlnTomoTomogramBinning")
    size_x: schema.Series[int] = schema.Field("rlnTomoSizeX")
    size_y: schema.Series[int] = schema.Field("rlnTomoSizeY")
    size_z: schema.Series[int] = schema.Field("rlnTomoSizeZ")

    def zip(self) -> Iterator["TomoMeta"]:
        """Zip the fields into a list of tuples."""
        for val in zip(
            self.tomo_name,
            self.voltage,
            self.cs,
            self.amplitude_contrast,
            self.original_pixel_size,
            self.tomo_hand.cast(pl.Int32),
            self.optics_group_name
            if self.optics_group_name is not None
            else ["--"] * len(self.tomo_name),
            self.tomo_tilt_series_pixel_size
            if self.tomo_tilt_series_pixel_size is not None
            else self.original_pixel_size,
            self.tomogram_binning,
            self.size_x,
            self.size_y,
            self.size_z,
        ):
            yield TomoMeta(*val)


def _ith_or_none(series: schema.Series | None, i: int):
    if series is None:
        return None
    return series[i]
