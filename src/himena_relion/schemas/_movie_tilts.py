import starfile_rs.schema.pandas as schema


class MicrographsModel(schema.LoopDataModel):
    mic_name: schema.Series[str] = schema.Field("rlnMicrographName")
    optics_group: schema.Series[int] = schema.Field("rlnOpticsGroup")
    ctf_image: schema.Series[str] = schema.Field("rlnCtfImage", default=None)


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
    ctf_image: schema.Series[str] = schema.Field("rlnCtfImage", default=None)


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
