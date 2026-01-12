from dataclasses import dataclass
from himena.plugins import register_config, config_field, get_config


@dataclass
class RelionConfig:
    motioncor2: str = config_field(
        default="MotionCor2",
        label="MotionCor2 Executable",
        tooltip="Path to the MotionCor2 executable",
    )
    ctffind4: str = config_field(
        default="ctffind4",
        label="CTFFIND4 Executable",
        tooltip="Path to the CTFFIND4 executable",
    )
    fn_topaz_exe: str = config_field(
        default="relion_python_topaz",
        label="Topaz Executable",
        tooltip="Path to the Topaz executable",
    )
    batchruntomo: str = config_field(
        default="batchruntomo",
        label="Batchruntomo Executable",
        tooltip="Path to the IMOD batchruntomo executable",
    )
    aretomo2: str = config_field(
        default="AreTomo2",
        label="AreTomo2 Executable",
        tooltip="Path to the AreTomo2 executable",
    )
    cryocare: str = config_field(
        default="/public/EM/cryoCARE",
        label="cryoCARE Directory",
        tooltip="Path to the cryoCARE directory",
    )
    resmap: str = config_field(
        default="ResMap",
        label="ResMap Executable",
        tooltip="Path to the ResMap executable",
    )
    dynamight: str = config_field(
        default="relion_python_dynamight",
        label="DynaMight Executable",
        tooltip="Path to the DynaMight executable",
    )
    modelangelo: str = config_field(
        default="relion_python_modelangelo",
        label="ModelAngelo Executable",
        tooltip="Path to the ModelAngelo executable",
    )
    scratch_dir: str = config_field(
        default="",
        label="Scratch Directory",
        tooltip="Path to the scratch directory",
    )
    queuename: str = config_field(
        default="openmpi",
        label="Queue Name",
        tooltip="Name of the queue to which to submit the job",
    )
    qsub: str = config_field(
        default="sbatch",
        label="Queue Submission Command",
        tooltip="Name of the command used to submit scripts to the queue",
    )
    qsubscript: str = config_field(
        default="/public/EM/RELION/relion/bin/relion_qsub.csh",
        label="Standard Submission Script",
    )


register_config("himena-relion", "RELION", RelionConfig())


def get_motioncor2_exe() -> str:
    return _get_himena_relion_config().motioncor2


def get_ctffind4_exe() -> str:
    return _get_himena_relion_config().ctffind4


def get_topaz_exe() -> str:
    return _get_himena_relion_config().fn_topaz_exe


def get_batchruntomo_exe() -> str:
    return _get_himena_relion_config().batchruntomo


def get_aretomo2_exe() -> str:
    return _get_himena_relion_config().aretomo2


def get_resmap_exe() -> str:
    return _get_himena_relion_config().resmap


def get_dynamight_exe() -> str:
    return _get_himena_relion_config().dynamight


def get_modelangelo_exe() -> str:
    return _get_himena_relion_config().modelangelo


def get_cryocare_dir() -> str:
    return _get_himena_relion_config().cryocare


def get_qsubscript() -> str:
    return _get_himena_relion_config().qsubscript


def get_scratch_dir() -> str:
    return _get_himena_relion_config().scratch_dir


def get_queue_dict() -> dict[str, str]:
    config = _get_himena_relion_config()
    return {
        "queuename": config.queuename,
        "qsub": config.qsub,
        "qsubscript": config.qsubscript,
    }


def _get_himena_relion_config() -> RelionConfig:
    config = get_config(RelionConfig, "himena-relion")
    if config is None:
        raise RuntimeError("RELION configuration not found.")
    return config
