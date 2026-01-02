from pathlib import Path
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


class ParticleMetaModel(schema.StarModel):
    particles: ParticlesModel = schema.Field()


class ModelClasses(schema.LoopDataModel):
    """This is also used for class_averages.star of select interactive job."""

    ref_image: schema.Series[str] = schema.Field("rlnReferenceImage")
    """Reference image in 000000XXX@Class2D/jobXXX/*.mrcs format."""
    class_distribution: schema.Series[float] = schema.Field("rlnClassDistribution")
    resolution: schema.Series[float] = schema.Field("rlnEstimatedResolution")


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


class MicCoordSetModel(schema.LoopDataModel):
    """Model for coordinate star files."""

    micrographs: schema.Series[str] = schema.Field("rlnMicrographName")
    coords: schema.Series[str] = schema.Field("rlnMicrographCoordinates")


class CoordsModel(schema.LoopDataModel):
    """Model for coordinate files inside Movies/ directory."""

    x: schema.Series[float] = schema.Field("rlnCoordinateX")
    y: schema.Series[float] = schema.Field("rlnCoordinateY")
    fom: schema.Series[float] = schema.Field("rlnAutopickFigureOfMerit", default=None)
