from pathlib import Path
import polars as pl
import starfile_rs.schema.polars as schema
from himena_relion.schemas._movie_tilts import TomogramsGroupModel


class OptimisationSetModel(schema.SingleDataModel):
    tomogram_star: Path = schema.Field("rlnTomoTomogramsFile")
    particles_star: Path = schema.Field("rlnTomoParticlesFile")
    trajectories_star: Path = schema.Field("rlnTomoTrajectoriesFile", default=None)

    def read_tomogram_model(self) -> TomogramsGroupModel:
        return TomogramsGroupModel.validate_file(self.tomogram_star)


class JobModel(schema.SingleDataModel):
    job_type_label: str = schema.Field("rlnJobTypeLabel")
    job_is_continue: int = schema.Field("rlnJobIsContinue")
    job_is_tomo: int = schema.Field("rlnJobIsTomo")


class JobOptionsValues(schema.LoopDataModel):
    variable: schema.Series[str] = schema.Field("rlnJobOptionVariable")
    value: schema.Series[str] = schema.Field("rlnJobOptionValue")

    def to_dict(self) -> dict[str, str]:
        """Return the parameters as a dictionary."""
        return dict(zip(self.variable, self.value))


class JobStarModel(schema.StarModel):
    job: JobModel = schema.Field()
    joboptions_values: JobOptionsValues = schema.Field()

    Job = JobModel
    Options = JobOptionsValues


class ParticlesModel(schema.LoopDataModel):
    tomo_name: schema.Series[str] = schema.Field("rlnTomoName", default=None)
    centered_x: schema.Series[float] = schema.Field(
        "rlnCenteredCoordinateXAngst", default=None
    )
    centered_y: schema.Series[float] = schema.Field(
        "rlnCenteredCoordinateYAngst", default=None
    )
    centered_z: schema.Series[float] = schema.Field(
        "rlnCenteredCoordinateZAngst", default=None
    )
    orig_x: schema.Series[float] = schema.Field("rlnOriginXAngst", default=None)
    orig_y: schema.Series[float] = schema.Field("rlnOriginYAngst", default=None)
    orig_z: schema.Series[float] = schema.Field("rlnOriginZAngst", default=None)
    class_number: schema.Series[int] = schema.Field("rlnClassNumber", default=None)
    angle_rot: schema.Series[float] = schema.Field("rlnAngleRot", default=None)
    angle_tilt: schema.Series[float] = schema.Field("rlnAngleTilt", default=None)

    @classmethod
    def example(cls, size: int) -> "ParticleMetaModel":
        s0 = size // 2
        s1 = size - s0
        return cls(
            tomo_name=pl.Series(["TS_01"] * s0 + ["TS_02"] * s1, dtype=pl.String),
            centered_x=pl.Series([0.0] * size, dtype=pl.Float64),
            centered_y=pl.Series([1.0] * size, dtype=pl.Float64),
            centered_z=pl.Series([2.0] * size, dtype=pl.Float64),
            orig_x=pl.Series([0.0] * size, dtype=pl.Float64),
            orig_y=pl.Series([0.0] * size, dtype=pl.Float64),
            orig_z=pl.Series([0.0] * size, dtype=pl.Float64),
            class_number=pl.Series([1] * size, dtype=pl.Int64),
            angle_rot=pl.Series([5.0] * size, dtype=pl.Float64),
            angle_tilt=pl.Series([8.0] * size, dtype=pl.Float64),
        )


class ParticleMetaModel(schema.StarModel):
    particles: ParticlesModel = schema.Field()

    @classmethod
    def example(cls, size: int) -> "ParticleMetaModel":
        """Create an example model with given size."""
        return cls(particles=ParticlesModel.example(size))


class ModelClasses(schema.LoopDataModel):
    """This is also used for class_averages.star of select interactive job."""

    ref_image: schema.Series[str] = schema.Field("rlnReferenceImage")
    """Reference image in 000000XXX@Class2D/jobXXX/*.mrcs format."""
    class_distribution: schema.Series[float] = schema.Field("rlnClassDistribution")
    resolution: schema.Series[float] = schema.Field("rlnEstimatedResolution")
    accuracy_rotation: schema.Series[float] = schema.Field(
        "rlnAccuracyRotations", default=None
    )
    accyracy_translation: schema.Series[float] = schema.Field(
        "rlnAccuracyTranslationsAngst", default=None
    )


class ModelGroups(schema.LoopDataModel):
    number: schema.Series[int] = schema.Field("rlnGroupNumber")
    """ID number of this group."""
    name: schema.Series[str] = schema.Field("rlnGroupName")
    """Name of this group."""
    num_particles: schema.Series[int] = schema.Field("rlnGroupNrParticles")
    """The number of particles assigned to this group."""
    scale_correction: schema.Series[float] = schema.Field(
        "rlnGroupScaleCorrection", default=None
    )


class ModelStarModel(schema.StarModel):
    """Model for the run_it???_model.star files."""

    classes: ModelClasses = schema.Field("model_classes")
    groups: ModelGroups = schema.Field("model_groups")

    @classmethod
    def example(cls, size: int) -> "ModelStarModel":
        """Create an example model with given size."""
        return cls(
            classes=ModelClasses(
                ref_image=pl.Series(
                    [
                        f"000000{ith:03d}@Class2D/job001/000000001.mrcs"
                        for ith in range(size)
                    ],
                    dtype=pl.String,
                ),
                class_distribution=pl.Series([1.0 / size] * size, dtype=pl.Float64),
                resolution=pl.Series([5.0] * size, dtype=pl.Float64),
                accuracy_rotation=pl.Series([0.5] * size, dtype=pl.Float64),
                accyracy_translation=pl.Series([1.0] * size, dtype=pl.Float64),
            ),
            groups=ModelGroups(
                number=pl.Series([1] * size, dtype=pl.Int64),
                name=pl.Series(["Group1"] * size, dtype=pl.String),
                num_particles=pl.Series([100] * size, dtype=pl.Int64),
                scale_correction=pl.Series([1.0] * size, dtype=pl.Float64),
            ),
        )


class MicCoordSetModel(schema.LoopDataModel):
    """Model for coordinate star files."""

    micrographs: schema.Series[str] = schema.Field("rlnMicrographName")
    coords: schema.Series[str] = schema.Field("rlnMicrographCoordinates")


class CoordsModel(schema.LoopDataModel):
    """Model for coordinate files, inside Movies/ directory or run_data.star"""

    x: schema.Series[float] = schema.Field("rlnCoordinateX")
    y: schema.Series[float] = schema.Field("rlnCoordinateY")
    fom: schema.Series[float] = schema.Field("rlnAutopickFigureOfMerit", default=None)
    orig_x: schema.Series[float] = schema.Field("rlnOriginXAngst", default=None)
    orig_y: schema.Series[float] = schema.Field("rlnOriginYAngst", default=None)
    class_number: schema.Series[int] = schema.Field("rlnClassNumber", default=None)
    angle_rot: schema.Series[float] = schema.Field("rlnAngleRot", default=None)
    angle_tilt: schema.Series[float] = schema.Field("rlnAngleTilt", default=None)
    image_name: schema.Series[str] = schema.Field("rlnImageName", default=None)
    """Particle image, such as 00000113@Extract/job009/Movies/XYZ_frameImage.mrcs"""
    mic_name: schema.Series[str] = schema.Field("rlnMicrographName", default=None)
    """Micrograph, such as MotionCorr/job002/Movies/XYZ_frameImage.mrc"""
