from pathlib import Path
import starfile_rs.schema.pandas as schema
from himena_relion.schemas._tilt_series import TomogramsGroupModel


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
    tomo_name: schema.Series[str] = schema.Field("rlnTomoName")
    centered_x: schema.Series[float] = schema.Field("rlnCenteredCoordinateXAngst")
    centered_y: schema.Series[float] = schema.Field("rlnCenteredCoordinateYAngst")
    centered_z: schema.Series[float] = schema.Field("rlnCenteredCoordinateZAngst")
    class_number: schema.Series[int] = schema.Field("rlnClassNumber")


class ParticleMetaModel(schema.StarModel):
    particles: ParticlesModel = schema.Field()
