from pathlib import Path

from himena import MainWindow
from himena.plugins import when_reader_used
from himena.workflow import LocalReaderMethod
from himena_relion._job_dir import JobDirectory
from himena_relion.consts import Type
from himena_relion.relion5 import _builtins as _spa
from himena_relion.relion5_tomo import _builtins as _tomo
from ._fake_relion import default_kwargs, start_new_project
from ._utils import JOBS_DIR_SPA, JOBS_DIR_TOMO

def _iter_execute_suggestion(ui: MainWindow, path):
    job_dir = JobDirectory(path)
    pre = job_dir._to_job_class()
    type_pre = Type.RELION_JOB + "." + pre.himena_model_type()
    reg = when_reader_used(type_pre)._registry
    meth = LocalReaderMethod(output_model_type=type_pre, path=job_dir.path)
    ui.read_file(path)
    for suggest in reg.iter_suggestion(type_pre, meth):
        suggest.execute(ui, meth)

def _suggested_command_ids(model_type: str) -> list[str]:
    """Command IDs suggested in the window of a job of the model type."""
    reg = when_reader_used(model_type)._registry
    meth = LocalReaderMethod(output_model_type=model_type, path=Path("dummy"))
    return [suggest.command_id for suggest in reg.iter_suggestion(model_type, meth)]

def test_no_duplicated_suggestions():
    """A job must not be suggested twice in a job window.

    Jobs connected from a type are also suggested for its subtypes (relion.extract and
    relion.extract.reextract), and some job classes share a type (full and half
    tomogram reconstruction).
    """
    from collections import Counter
    from himena_relion._job_class import CONNECTED_JOBS

    pre_types = {Type.RELION_JOB + "." + pre.himena_model_type() for pre, _ in CONNECTED_JOBS}
    for model_type in pre_types:
        counts = Counter(_suggested_command_ids(model_type))
        assert [cid for cid, n in counts.items() if n > 1] == [], model_type

def test_suggestions_of_subtypes():
    from himena_relion.relion5_tomo import SelectTomograms

    def suggested(job_path: Path) -> list[str]:
        return _suggested_command_ids(JobDirectory(job_path).himena_model_type())

    select_tomo = SelectTomograms.command_id()
    pick = _tomo.PickJob.command_id()
    # tomograms are reconstructed by AreTomo2
    assert {select_tomo, pick} <= set(suggested(JOBS_DIR_TOMO / "AlignTiltSeries/job004"))
    # tilt series alignment does not output tomograms
    for job in ["job001", "job002", "job003"]:
        ids = suggested(JOBS_DIR_TOMO / "AlignTiltSeries" / job)
        assert select_tomo not in ids and pick not in ids, job
    # jobs connected from Extract are also suggested from Re-extract
    ids_extract = suggested(JOBS_DIR_SPA / "Extract/job001")
    ids_reextract = suggested(JOBS_DIR_SPA / "Extract/job002")
    assert _spa.Class2DJob.command_id() in ids_extract
    assert set(ids_extract) <= set(ids_reextract)
    assert _spa.Refine3DJob.command_id() in ids_reextract

def test_initial_model_to_refine(himena_ui):
    _iter_execute_suggestion(himena_ui, JOBS_DIR_SPA / "InitialModel" / "job001")
    _iter_execute_suggestion(himena_ui, JOBS_DIR_SPA / "Class3D" / "job001")
    _iter_execute_suggestion(himena_ui, JOBS_DIR_SPA / "Class3D" / "job002")
    _iter_execute_suggestion(himena_ui, JOBS_DIR_SPA / "Refine3D" / "job001")


def _contexts(ui: MainWindow, job_path: Path) -> dict[str, dict]:
    """Map from the suggested command to the parameters given to the scheduler."""
    job_dir = JobDirectory(job_path)
    model_type = job_dir.himena_model_type()
    reg = when_reader_used(model_type)._registry
    meth = LocalReaderMethod(output_model_type=model_type, path=job_dir.path)
    return {
        suggest.command_id: suggest.user_context(ui, meth)
        for suggest in reg.iter_suggestion(model_type, meth)
    }


def test_spa_refinement_cycle(himena_ui: MainWindow, in_project: Path, relion):
    start_new_project(himena_ui, in_project)
    _spa.Refine3DJob.create_job(
        _cwd=in_project,
        **default_kwargs(
            _spa.Refine3DJob,
            fn_img="Extract/job099/particles.star",
            fn_ref="InitialModel/job098/initial_model.mrc",
            fn_mask="MaskCreate/job097/mask.mrc",
            particle_diameter=180,
        ),
    )
    _spa.MaskCreationJob.create_job(
        _cwd=in_project,
        **default_kwargs(_spa.MaskCreationJob, fn_in="Refine3D/job001/run_class001.mrc"),
    )
    _spa.PostProcessJob.create_job(
        _cwd=in_project,
        **default_kwargs(
            _spa.PostProcessJob,
            fn_in="Refine3D/job001/run_half1_class001_unfil.mrc",
            fn_mask="MaskCreate/job002/mask.mrc",
        ),
    )
    refine = _contexts(himena_ui, in_project / "Refine3D/job001")
    assert refine["relion.postprocess"] == {
        "fn_in": "Refine3D/job001/run_half1_class001_unfil.mrc",
        "fn_mask": "MaskCreate/job097/mask.mrc",
    }
    assert refine["relion.class3d.alignment"] == {
        "fn_img": "Refine3D/job001/run_data.star",
        "fn_ref": "Refine3D/job001/run_class001.mrc",
        "fn_mask": "MaskCreate/job097/mask.mrc",
        "particle_diameter": 180.0,
    }
    assert refine["relion.maskcreate"] == {"fn_in": "Refine3D/job001/run_class001.mrc"}
    assert refine["relion.refine3d.continue"]["_job_dir"].job_normal_id() == (
        "Refine3D/job001/"
    )

    # the half map is searched from the parent of MaskCreate
    mask = _contexts(himena_ui, in_project / "MaskCreate/job002")
    assert mask["relion.postprocess"] == {
        "fn_in": "Refine3D/job001/run_half1_class001_unfil.mrc",
        "fn_mask": "MaskCreate/job002/mask.mrc",
    }

    # the particles are searched from the parents of PostProcess
    post = _contexts(himena_ui, in_project / "PostProcess/job003")
    assert post["relion.ctfrefine"] == {
        "fn_data": "Refine3D/job001/run_data.star",
        "fn_post": "PostProcess/job003/postprocess.star",
    }
    assert post["modelangelo"] == {"fn_map": "PostProcess/job003/postprocess_masked.mrc"}


def test_tomo_refinement_cycle(himena_ui: MainWindow, in_project: Path, relion):
    relion.input_labels["optimisation_set.star"] = "TomoOptimisationSet.star.relion"
    start_new_project(himena_ui, in_project)
    optim = "Extract/job099/optimisation_set.star"
    _tomo.ReconstructParticlesJob.create_job(
        _cwd=in_project,
        **default_kwargs(
            _tomo.ReconstructParticlesJob,
            in_optim={"in_optimisation": optim},
            binning=2,
            box_size=96,
            crop_size=64,
        ),
    )
    _spa.MaskCreationJob.create_job(
        _cwd=in_project,
        **default_kwargs(_spa.MaskCreationJob, fn_in="Reconstruct/job001/merged.mrc"),
    )
    _tomo.PostProcessTomoJob.create_job(
        _cwd=in_project,
        **default_kwargs(
            _tomo.PostProcessTomoJob,
            fn_in="Reconstruct/job001/half1.mrc",
            fn_mask="MaskCreate/job002/mask.mrc",
        ),
    )
    cycle_kwargs = dict(
        in_optim={"in_optimisation": optim},
        in_halfmaps="Reconstruct/job001/half1.mrc",
        in_refmask="MaskCreate/job002/mask.mrc",
        in_post="PostProcess/job003/postprocess.star",
        box_size=64,
    )
    _tomo.CtfRefineTomoJob.create_job(
        _cwd=in_project, **default_kwargs(_tomo.CtfRefineTomoJob, **cycle_kwargs)
    )
    _tomo.FrameAlignTomoJob.create_job(
        _cwd=in_project,
        **default_kwargs(_tomo.FrameAlignTomoJob, do_motion=True, **cycle_kwargs),
    )
    _tomo.FrameAlignTomoJob.create_job(
        _cwd=in_project, **default_kwargs(_tomo.FrameAlignTomoJob, **cycle_kwargs)
    )
    _tomo.ReconstructParticlesJob.create_job(
        _cwd=in_project,
        **default_kwargs(
            _tomo.ReconstructParticlesJob,
            in_optim={"in_optimisation": "CtfRefine/job004/optimisation_set.star"},
        ),
    )
    _tomo.Refine3DTomoJob.create_job(
        _cwd=in_project,
        **default_kwargs(
            _tomo.Refine3DTomoJob,
            in_optim={"in_optimisation": optim},
            fn_ref="Reconstruct/job001/merged.mrc",
            fn_mask="MaskCreate/job002/mask.mrc",
        ),
    )
    _tomo.PostProcessTomoJob.create_job(
        _cwd=in_project,
        **default_kwargs(
            _tomo.PostProcessTomoJob,
            fn_in="Refine3D/job008/run_half1_class001_unfil.mrc",
            fn_mask="MaskCreate/job002/mask.mrc",
        ),
    )
    ctf_refine = _tomo.CtfRefineTomoJob.command_id()
    frame_align = _tomo.FrameAlignTomoJob.command_id()
    reconstruct = _tomo.ReconstructParticlesJob.command_id()
    extract = _tomo.ExtractParticlesTomoJob.command_id()
    post_process = _tomo.PostProcessTomoJob.command_id()
    refine = _tomo.Refine3DTomoJob.command_id()

    # Reconstruct -> PostProcess / Extract
    ctx = _contexts(himena_ui, in_project / "Reconstruct/job001")
    assert ctx[post_process] == {"fn_in": "Reconstruct/job001/half1.mrc"}
    assert ctx[extract] == {
        "in_optim": {"in_optimisation": "Reconstruct/job001/optimisation_set.star"},
        "binning": 2,
        "box_size": 96,
        "crop_size": 64,
    }
    assert ctx[refine] == {
        "in_optim": {"in_optimisation": optim},
        "fn_ref": "Reconstruct/job001/merged.mrc",
        "particle_diameter": 200.0,  # pixel size is unknown
        "ref_correct_greyscale": True,
    }
    # the mask is inherited from the parent CtfRefine job
    ctx = _contexts(himena_ui, in_project / "Reconstruct/job007")
    assert ctx[post_process] == {
        "fn_in": "Reconstruct/job007/half1.mrc",
        "fn_mask": "MaskCreate/job002/mask.mrc",
    }

    # MaskCreate -> PostProcess: the half map is searched from the parent
    ctx = _contexts(himena_ui, in_project / "MaskCreate/job002")
    assert ctx[post_process] == {
        "fn_in": "Reconstruct/job001/half1.mrc",
        "fn_mask": "MaskCreate/job002/mask.mrc",
    }

    # PostProcess -> CtfRefine / FrameAlign: the inputs are searched from the parents
    ctx = _contexts(himena_ui, in_project / "PostProcess/job003")
    expected = {
        "in_optim": {"in_optimisation": optim},
        "in_halfmaps": "Reconstruct/job001/half1.mrc",
        "in_refmask": "MaskCreate/job002/mask.mrc",
        "in_post": "PostProcess/job003/postprocess.star",
        "box_size": "64",
    }
    assert ctx[ctf_refine] == expected
    assert ctx[frame_align] == expected
    # ... also after Refine3D
    ctx = _contexts(himena_ui, in_project / "PostProcess/job009")
    expected = {
        "in_optim": {"in_optimisation": "Refine3D/job008/run_optimisation_set.star"},
        "in_halfmaps": "Refine3D/job008/run_half1_class001_unfil.mrc",
        "in_refmask": "MaskCreate/job002/mask.mrc",
        "in_post": "PostProcess/job009/postprocess.star",
    }
    assert ctx[ctf_refine] == expected
    assert ctx[frame_align] == expected

    # CtfRefine -> Reconstruct / Refine3D
    ctx = _contexts(himena_ui, in_project / "CtfRefine/job004")
    assert ctx[reconstruct] == {
        "in_optim": {"in_optimisation": "CtfRefine/job004/optimisation_set.star"},
        "box_size": "64",
        "crop_size": "64",
    }
    assert ctx[refine] == {
        "in_optim": {"in_optimisation": "CtfRefine/job004/optimisation_set.star"},
        "fn_mask": "MaskCreate/job002/mask.mrc",
    }

    # FrameAlign -> Extract: the outputs depend on whether the motion was fitted
    ctx = _contexts(himena_ui, in_project / "Polish/job005")
    assert ctx[extract] == {
        "in_optim": {
            "in_particles": "Polish/job005/particles.star",
            "in_tomograms": "Polish/job005/tomograms.star",
            "in_trajectories": "Polish/job005/motion.star",
        }
    }
    ctx = _contexts(himena_ui, in_project / "Polish/job006")
    assert ctx[extract] == {"in_optim": {"in_tomograms": "Polish/job006/tomograms.star"}}
    # the particles are read from the input optimisation set if exists
    in_project.joinpath("Extract/job099").mkdir(parents=True)
    in_project.joinpath(optim).write_text(
        "data_\n\n"
        "_rlnTomoParticlesFile Extract/job099/particles.star\n"
        "_rlnTomoTomogramsFile Tomograms/job098/tomograms.star\n",
        newline="\n",
    )
    ctx = _contexts(himena_ui, in_project / "Polish/job006")
    assert ctx[extract] == {
        "in_optim": {
            "in_particles": "Extract/job099/particles.star",
            "in_tomograms": "Polish/job006/tomograms.star",
        }
    }
