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
    # SPA
    "relion.import.movies": "Import Movies",
    "relion.import.other": "Import Others",
    "relion.motioncorr.motioncor2": "Motion Corr.",
    "relion.motioncorr.own": "Motion Corr.",
    "relion.ctffind.ctffind4": "CTF Estimation",
    "relion.manualpick": "Manual Pick",
    "relion.autopick.log": "LoG Pick",
    "relion.autopick.ref2d": "Template Pick",
    "relion.autopick.ref3d": "Template Pick 3D",
    "relion.autopick.topaz.train": "Topaz Train",
    "relion.autopick.topaz.pick": "Topaz Pick",
    "relion.extract": "Extract",
    "relion.extract.reextract": "Re-extract",
    "relion.class2d": "2D Class",
    "relion.initialmodel": "Initial Model",
    "relion.refine3d": "Auto Refine",
    "relion.class3d": "3D Class",
    "dynamight": "DynaMight",
    "modelangelo": "ModelAngelo",
    "relion.multibody": "Multi-body Refinement",
    "relion.ctfrefine": "CTF Refine",
    "relion.ctfrefine.anisomag": "CTF Refine",
    "relion.polish.train": "Bayesian Polish (Train)",
    "relion.polish": "Bayesian Polish",
    "relion.localres.own": "Local Resolution",
    "relion.localres.resmap": "Local Resolution",
    # Tomo
    "relion.importtomo": "Import Tomo",
    "relion.excludetilts": "Exclude Tilts",
    "relion.aligntiltseries": "Align Tilts",
    "relion.reconstructtomograms": "Reconstruct Tomos",
    "relion.denoisetomo": "Denoise",
    "relion.picktomo": "Manual Pick",
    "relion.pseudosubtomo": "Extract Subtomo",
    "relion.initialmodel.tomo": "Initial Model",
    "relion.refine3d.tomo": "Auto Refine",
    "relion.reconstructparticletomo": "Reconstruct Particles",
    "relion.select.interactive": "Select Class",
    "relion.select.class2dauto": "Class Ranker",
    "relion.select.onvalue": "Select On Value",
    "relion.select.split": "Split Particles",
    "relion.select.filamentsdendrogram": "Select Filaments",
    "relion.select.removeduplicates": "Remove Duplicates",
    "relion.postprocess": "Post Process",
    "relion.maskcreate": "Create Mask",
    "relion.joinstar.particles": "Join Particles",
    "relion.joinstar.micrographs": "Join Micrographs",
    "relion.joinstar.movies": "Join Movies",
    "relion.framealigntomo": "Frame Align",
    "relion.ctfrefinetomo": "CTF Refine",
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
