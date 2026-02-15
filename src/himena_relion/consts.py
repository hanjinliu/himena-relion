from enum import Enum
from himena.plugins import configure_submenu


class Type:
    RELION_JOB = "relion_job"
    RELION_PIPELINE = "relion_pipeline"


class MenuId:
    RELION = "tools/relion"
    RELION_UTILS = "tools/relion/990_utils"

    RELION_IMPORT_JOB = "tools/relion/000_import"
    RELION_PREPROCESS_JOB = "tools/relion/003_preprocess"
    RELION_PICK_JOB = "tools/relion/100_pick"
    RELION_EXTRACT_JOB = "tools/relion/102_extract"
    RELION_FILTER_PARTICLES_JOB = "tools/relion/110_filter_particles"
    RELION_RECONSTRUCTION_JOB = "tools/relion/400_reconstruction"
    RELION_REFINE_JOB = "tools/relion/500_refine"
    RELION_POSTPROCESS_JOB = "tools/relion/600_postprocess"
    RELION_UTILS_JOB = "tools/relion/990_utils"

    RELION_TILT_ALIGN_JOB = "tools/relion/030_tilt_align"
    RELION_TOMO_RECON_JOB = "tools/relion/036_tomo_reconstruction"

    RELION_OTHER_JOB = "tools/relion/999_others"


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
    "relion.ctfrefine.anisomag": "CTF Refine (Aniso. Mag.)",
    "relion.polish.train": "Bayesian Polish (Train)",
    "relion.polish": "Bayesian Polish",
    "relion.localres.own": "Local Res (RELION)",
    "relion.localres.resmap": "Local Res (ResMap)",
    "relion.subtract": "Subtract Particles",
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
configure_submenu(MenuId.RELION_UTILS, "Job Actions")
configure_submenu(MenuId.RELION_IMPORT_JOB, "Job: Import")
configure_submenu(MenuId.RELION_PREPROCESS_JOB, "Job: Preprocess")
configure_submenu(MenuId.RELION_PICK_JOB, "Job: Pick")
configure_submenu(MenuId.RELION_EXTRACT_JOB, "Job: Extract")
configure_submenu(MenuId.RELION_FILTER_PARTICLES_JOB, "Job: Filter Particles")
configure_submenu(MenuId.RELION_RECONSTRUCTION_JOB, "Job: Reconstruction")
configure_submenu(MenuId.RELION_UTILS_JOB, "Job: Utilities")
configure_submenu(MenuId.RELION_TILT_ALIGN_JOB, "Job: Tilt Align")
configure_submenu(MenuId.RELION_TOMO_RECON_JOB, "Job: Tomo Reconstruction")
configure_submenu(MenuId.RELION_REFINE_JOB, "Job: Refine")
configure_submenu(MenuId.RELION_POSTPROCESS_JOB, "Job: Postprocess")
configure_submenu(MenuId.RELION_OTHER_JOB, "Job: Other Jobs")
