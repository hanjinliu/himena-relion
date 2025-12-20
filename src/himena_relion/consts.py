from enum import Enum
from himena.plugins import configure_submenu


class Type:
    RELION_JOB = "relion_job"
    RELION_PIPELINE = "relion_pipeline"


class MenuId:
    RELION = "tools/relion"
    RELION_NEW_JOB = "tools/relion/new"
    RELION_UTILS = "tools/relion/utils"


class RelionJobState(Enum):
    EXIT_SUCCESS = "exit_success"
    EXIT_FAILURE = "exit_failure"
    EXIT_ABORTED = "exit_aborted"
    ABORT_NOW = "abort_now"
    RUNNING = "running"


class FileNames:
    EXIT_SUCCESS = "RELION_JOB_EXIT_SUCCESS"
    EXIT_FAILURE = "RELION_JOB_EXIT_FAILURE"
    EXIT_ABORTED = "RELION_JOB_EXIT_ABORTED"
    ABORT_NOW = "RELION_JOB_ABORT_NOW"


class RelionNodeTypeLabels:
    TOMO_GROUP_META = "TomogramGroupMetadata"
    PARTICLES_GROUP_META = "ParticleGroupMetadata"
    TOMO_OPT_STAR = "TomoOptimisationSet"
    DENSITY_MAP = "DensityMap"
    MASK = "Mask3D"
    PROCESSED_DATA = "ProcessData"


JOB_ID_MAP = {
    "relion.importtomo": "Import Tomo",
    "relion.motioncorr.motioncor2": "Motion Corr.",
    "relion.motioncorr.own": "Motion Corr.",
    "relion.ctffind.ctffind4": "CTF Estimation",
    "relion.excludetilts": "Exclude Tilts",
    "relion.aligntiltseries": "Align Tilts",
    "relion.reconstructtomograms": "Reconstruct Tomos",
    "relion.denoisetomo": "Denoise",
    "relion.picktomo": "Pick Tomo",
    "relion.pseudosubtomo": "Extract",
    "relion.initialmodel.tomo": "Initial Model",
    "relion.refine3d.tomo": "Auto Refine",
    "relion.class3d": "3D Class",
    "relion.reconstructparticletomo": "Reconstruct Particles",
    "relion.select.interactive": "Select Class",
    "relion.select.removeduplicates": "Remove Duplicates",
    "relion.postprocess": "Post Process",
    "relion.maskcreate": "Create Mask",
    "relion.joinstar.particles": "Join Particles",
    "relion.joinstar.micrographs": "Join Micrographs",
    "relion.framealigntomo": "Frame Align",
    "relion.ctfrefinetomo": "CTF Refine",
    "modelangelo": "ModelAngelo",
}

JOB_IMPORT_PATH_FILE = "JOB_IMPORT_PATH.txt"

ARG_NAME_REMAP = [
    ("in_mics", "in_mic"),
    ("in_movies", "in_mov"),
    ("in_parts", "in_part"),
    ("j", "nr_threads"),
]

configure_submenu(MenuId.RELION, "RELION")
configure_submenu(MenuId.RELION_NEW_JOB, "New Job")
