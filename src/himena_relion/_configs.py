import os
from pathlib import Path
import shutil
from dataclasses import dataclass
import subprocess
from himena.plugins import register_config, config_field, get_config


@dataclass
class RelionConfig:
    motioncor2: str = config_field(
        default="MotionCor2",
        label="<code>MotionCor2</code> Executable",
        tooltip=(
            "Path to the MotionCor2 executable. Use 'MotionCor2' if it's already in\n"
            "your PATH."
        ),
    )
    ctffind4: str = config_field(
        default="ctffind4",
        label="<code>CTFFIND4</code> Executable",
        tooltip=(
            "Path to the CTFFIND4 executable. Use 'ctffind4' if it's already in\n"
            "your PATH."
        ),
    )
    batchruntomo: str = config_field(
        default="batchruntomo",
        label="<code>Batchruntomo</code> Executable",
        tooltip=(
            "Path to the IMOD batchruntomo executable. Use 'batchruntomo' if it's\n"
            "already in your PATH."
        ),
    )
    aretomo2: str = config_field(
        default="AreTomo2",
        label="<code>AreTomo2</code> Executable",
        tooltip=(
            "Path to the AreTomo2 executable. Use 'AreTomo2' if it's already in your\n"
            "PATH."
        ),
    )
    cryocare: str = config_field(
        default="/public/EM/cryoCARE",
        label="<code>cryoCARE</code> Directory",
        tooltip="Path to the cryoCARE directory",
    )
    resmap: str = config_field(
        default="ResMap",
        label="<code>ResMap</code> Executable",
        tooltip=(
            "Path to the ResMap executable. Use 'ResMap' if it's already in your PATH."
        ),
    )
    chimera: str = config_field(
        default="chimerax",
        label="UCSF <code>ChimeraX</code> or <code>Chimera</code> Executable",
        tooltip=(
            "Path to the ChimeraX or Chimera executable. Use 'chimerax' or 'chimera' "
            "if it's already in your PATH."
        ),
    )
    scratch_dir: str = config_field(
        default="",
        label="Scratch Directory",
        tooltip="Path to the scratch directory.",
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


def get_relion_pipeliner_exe() -> str:
    # in the future, RELION may support using multiple executables from different
    # versions. For now, we just return the command name itself
    return "relion_pipeliner"


def get_motioncor2_exe() -> str:
    return _get_himena_relion_config().motioncor2


def get_ctffind4_exe() -> str:
    return _may_expand_user(_get_himena_relion_config().ctffind4)


def get_topaz_exe() -> str:
    if pipeliner_path := _pipeliner_path():
        return pipeliner_path.with_name("relion_python_topaz")
    return "relion_python_topaz"


def get_batchruntomo_exe() -> str:
    return _may_expand_user(_get_himena_relion_config().batchruntomo)


def get_aretomo2_exe() -> str:
    return _may_expand_user(_get_himena_relion_config().aretomo2)


def get_resmap_exe() -> str:
    return _may_expand_user(_get_himena_relion_config().resmap)


def get_dynamight_exe() -> str:
    if pipeliner_path := _pipeliner_path():
        return pipeliner_path.with_name("relion_python_dynamight")
    return "relion_python_dynamight"


def get_modelangelo_exe() -> str:
    if pipeliner_path := _pipeliner_path():
        return pipeliner_path.with_name("relion_python_modelangelo")
    return "relion_python_modelangelo"


def get_cryocare_dir() -> str:
    return _may_expand_user(_get_himena_relion_config().cryocare)


def get_chimera_exe() -> str:
    return _may_expand_user(_get_himena_relion_config().chimera)


def get_qsubscript() -> str:
    return _may_expand_user(_get_himena_relion_config().qsubscript)


def get_scratch_dir() -> str:
    return _may_expand_user(_get_himena_relion_config().scratch_dir)


def get_queue_dict() -> dict[str, str]:
    config = _get_himena_relion_config()
    return {
        "queuename": config.queuename,
        "qsub": config.qsub,
        "qsubscript": config.qsubscript,
    }


def open_in_chimerax(path: str | Path) -> None:
    """Open the given file in ChimeraX or Chimera.

    This function requires `himena` application."""
    exe = get_chimera_exe()
    if shutil.which(exe) is None:
        raise RuntimeError(
            f"ChimeraX/Chimera executable '{exe}' not found. Please check your RELION "
            "configuration in the setting dialog (Ctrl+,)."
        )
    return open_in_external_app(path, exe)


def open_in_3dmod(path: str | Path) -> None:
    return open_in_imod_command(path, "3dmod")


def open_in_imod_command(path: str | Path, exe: str) -> None:
    if shutil.which(exe) is None:
        exe = str(Path(get_batchruntomo_exe()).parent.joinpath(exe))
        if shutil.which(exe) is None:
            raise RuntimeError(f"{exe} executable not found.")
    return open_in_external_app(path, exe)


def open_in_external_app(path: str | Path, command: str, *more_args) -> None:
    env = os.environ.copy()
    env.pop("QT_API", None)
    subprocess.Popen(
        [command, str(path), *more_args],
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


def _get_himena_relion_config() -> RelionConfig:
    config = get_config(RelionConfig, "himena-relion")
    if config is None:
        raise RuntimeError("RELION configuration not found.")
    return config


def _may_expand_user(path: str) -> str:
    if path.startswith("~/"):
        return str(Path(path).expanduser())
    return path


def _pipeliner_path() -> Path | None:
    path = shutil.which("relion_pipeliner")
    if path is not None:
        return Path(path)
    else:
        return None
