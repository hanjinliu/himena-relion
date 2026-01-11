from pathlib import Path
import pandas as pd
import starfile_rs.schema.pandas as schema
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
    value: schema.Series[object] = schema.Field("rlnJobOptionValue")

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
    class_number: schema.Series[int] = schema.Field("rlnClassNumber", default=None)
    angle_rot: schema.Series[float] = schema.Field("rlnAngleRot", default=None)
    angle_tilt: schema.Series[float] = schema.Field("rlnAngleTilt", default=None)

    @classmethod
    def example(cls, size: int) -> "ParticleMetaModel":
        s0 = size // 2
        s1 = size - s0
        return cls(
            tomo_name=pd.Series(["TS_01"] * s0 + ["TS_02"] * s1, dtype="string"),
            centered_x=pd.Series([0.0] * size, dtype="float"),
            centered_y=pd.Series([1.0] * size, dtype="float"),
            centered_z=pd.Series([2.0] * size, dtype="float"),
            class_number=pd.Series([1] * size, dtype="int"),
            angle_rot=pd.Series([5.0] * size, dtype="float"),
            angle_tilt=pd.Series([8.0] * size, dtype="float"),
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
                ref_image=pd.Series(
                    [
                        f"000000{ith:03d}@Class2D/job001/000000001.mrcs"
                        for ith in range(size)
                    ],
                    dtype="string",
                ),
                class_distribution=pd.Series([1.0 / size] * size, dtype="float"),
                resolution=pd.Series([5.0] * size, dtype="float"),
                accuracy_rotation=pd.Series([0.5] * size, dtype="float"),
                accyracy_translation=pd.Series([1.0] * size, dtype="float"),
            ),
            groups=ModelGroups(
                number=pd.Series([1] * size, dtype="int"),
                name=pd.Series(["Group1"] * size, dtype="string"),
                num_particles=pd.Series([100] * size, dtype="int"),
                scale_correction=pd.Series([1.0] * size, dtype="float"),
            ),
        )


class MicCoordSetModel(schema.LoopDataModel):
    """Model for coordinate star files."""

    micrographs: schema.Series[str] = schema.Field("rlnMicrographName")
    coords: schema.Series[str] = schema.Field("rlnMicrographCoordinates")


class CoordsModel(schema.LoopDataModel):
    """Model for coordinate files inside Movies/ directory."""

    x: schema.Series[float] = schema.Field("rlnCoordinateX")
    y: schema.Series[float] = schema.Field("rlnCoordinateY")
    fom: schema.Series[float] = schema.Field("rlnAutopickFigureOfMerit", default=None)
