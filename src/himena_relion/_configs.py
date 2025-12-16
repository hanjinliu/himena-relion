from dataclasses import dataclass
from himena.plugins import register_config, config_field, get_config


@dataclass
class RelionConfig:
    motioncor2: str = config_field(
        default="/public/EM/MOTIONCOR2/MotionCor2",
        label="MotionCor2 Executable",
        tooltip="Path to the MotionCor2 executable",
    )
    ctffind4: str = config_field(
        default="/public/EM/ctffind/ctffind.exe",
        label="CTFFIND4 Executable",
        tooltip="Path to the CTFFIND4 executable",
    )
    batchruntomo: str = config_field(
        default="/public/EM/imod/IMOD/bin/batchruntomo",
        label="Batchruntomo Executable",
        tooltip="Path to the IMOD batchruntomo executable",
    )
    aretomo2: str = config_field(
        default="/public/EM/AreTomo/AreTomo2/AreTomo2",
        label="AreTomo2 Executable",
        tooltip="Path to the AreTomo2 executable",
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


def get_batchruntomo_exe() -> str:
    return _get_himena_relion_config().batchruntomo


def get_aretomo2_exe() -> str:
    return _get_himena_relion_config().aretomo2


def get_qsubscript() -> str:
    return _get_himena_relion_config().qsubscript


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
