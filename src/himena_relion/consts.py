from enum import Enum


class Type:
    RELION_JOB = "relion_job"
    RELION_PIPELINE = "relion_pipeline"


class RelionJobState(Enum):
    EXIT_SUCCESS = "exit_success"
    EXIT_FAILURE = "exit_failure"
    EXIT_ABORTED = "exit_aborted"
    ABORT_NOW = "abort_now"
    RUNNING = "else"


JOB_ID_MAP = {
    "relion.importtomo": "Import Tomo",
    "relion.motioncorr.motioncor2": "Motion Corr.",
    "relion.motioncorr.own": "Motion Corr.",
    "relion.ctffind.ctffind4": "CTF Estimation",
    "relion.excludetilts": "Exclude Tilts",
    "relion.aligntiltseries": "Align Tilts",
    "relion.reconstructtomograms": "Reconstruct Tomos",
    "relion.denoisetomo": "Denoise",
    "relion.picktomo": "Pick",
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
}
