from himena import MainWindow
from himena.testing import choose_one_dialog_response
from himena_relion._job_dir import JobDirectory
from himena_relion._widgets._trash_widget import QTrashWidget, _copy_job_paths, _delete_permanently
from himena_relion.schemas import RelionPipelineModel
from himena_relion.io._impl import trash_job, restore_trashed_jobs
from ._utils import prep_relion_project


def test_trash_untrash(himena_ui: MainWindow, tmpdir):
    rln_dir = prep_relion_project(tmpdir)

    himena_ui.read_file(rln_dir / "default_pipeline.star")
    himena_ui.read_file(rln_dir / "MotionCorr/job002")
    himena_ui.read_file(rln_dir / "Import/job001")
    assert "job002" in himena_ui.tabs.names
    with choose_one_dialog_response(himena_ui, True):
        trash_job(himena_ui, JobDirectory(rln_dir / "MotionCorr/job002"))
    assert "job002" not in himena_ui.tabs.names
    assert (rln_dir / "Import/job001").exists()
    assert not (rln_dir / "MotionCorr/job002").exists()
    assert not (rln_dir / "CtfFind/job003").exists()
    assert rln_dir.joinpath("default_pipeline.star").exists()
    default_pipeline_text = rln_dir.joinpath("default_pipeline.star").read_text()
    assert "job001" in default_pipeline_text
    assert "job002" not in default_pipeline_text
    assert "job003" not in default_pipeline_text
    restore_trashed_jobs(rln_dir, ["MotionCorr/job002/"])
    default_pipeline_text = rln_dir.joinpath("default_pipeline.star").read_text()
    assert (rln_dir / "Import/job001").exists()
    assert (rln_dir / "MotionCorr/job002").exists()
    assert not (rln_dir / "CtfFind/job003").exists()
    assert "job001" in default_pipeline_text
    assert "job002" in default_pipeline_text
    assert "job003" not in default_pipeline_text
    restore_trashed_jobs(rln_dir, ["CtfFind/job003/"])
    default_pipeline_text = rln_dir.joinpath("default_pipeline.star").read_text()
    assert (rln_dir / "Import/job001").exists()
    assert (rln_dir / "MotionCorr/job002").exists()
    assert (rln_dir / "CtfFind/job003").exists()
    assert "job001" in default_pipeline_text
    assert "job002" in default_pipeline_text
    assert "job003" in default_pipeline_text

def test_trash_untrash_with_alias(himena_ui: MainWindow, tmpdir):
    import os

    rln_dir = prep_relion_project(tmpdir)
    p = RelionPipelineModel.validate_file(rln_dir / "default_pipeline.star")
    df = p.processes.dataframe
    df[1, 1] = "MotionCorr/alias-0/"
    (rln_dir / "default_pipeline.star").write_text(p.to_string())
    os.symlink(rln_dir / "MotionCorr/job002", rln_dir / "MotionCorr/alias-0", target_is_directory=True)

    himena_ui.read_file(rln_dir / "default_pipeline.star")
    assert rln_dir.joinpath("MotionCorr/alias-0").exists()
    with choose_one_dialog_response(himena_ui, True):
        trash_job(himena_ui, JobDirectory(rln_dir / "MotionCorr/alias-0"))
    assert not rln_dir.joinpath("MotionCorr/alias-0").exists()
    assert not rln_dir.joinpath("MotionCorr/job002").exists()

    restore_trashed_jobs(rln_dir, ["MotionCorr/job002/"])
    assert rln_dir.joinpath("MotionCorr/alias-0").exists()
    assert rln_dir.joinpath("MotionCorr/job002").exists()
    assert rln_dir.joinpath("MotionCorr/alias-0").resolve() == rln_dir.joinpath("MotionCorr/job002").resolve()

def test_trash_widget(himena_ui: MainWindow, tmpdir):
    rln_dir = prep_relion_project(tmpdir, delay_ms=5)
    himena_ui.read_file(rln_dir / "default_pipeline.star")
    with choose_one_dialog_response(himena_ui, True):
        trash_job(himena_ui, JobDirectory(rln_dir / "MotionCorr/job002"))
    win = himena_ui.read_file(rln_dir / "Trash")
    assert isinstance(win.widget, QTrashWidget)
    assert win.widget.trash_dir() == rln_dir / "Trash"

    list_widget = win.widget._job_list_widget
    win.widget._make_context_menu()
    list_widget.setCurrentRow(0)
    win.widget._make_context_menu()

    _copy_job_paths(["MotionCorr/job002/"], rln_dir / "Trash")
    assert (rln_dir / "Trash" / "MotionCorr/job002").exists()
    win.widget._update_job_list()
    # child jobs will also be moved to trash.
    assert [list_widget.item(i).text() for i in range(list_widget.count())] == ["MotionCorr/job002/", "CtfFind/job003/"]
    with choose_one_dialog_response(himena_ui, True):
        _delete_permanently(["MotionCorr/job002/"], rln_dir / "Trash", join=True)
    assert not (rln_dir / "Trash" / "MotionCorr/job002").exists()
    win.widget._update_job_list()
    assert [list_widget.item(i).text() for i in range(list_widget.count())] == ["CtfFind/job003/"]

    # Gentle/Harsh cleaned data will be move to Trash without job.star
    dir_clean = rln_dir / "Trash" / "Class3D" / "job003"
    dir_clean.mkdir(parents=True)
    dir_clean.joinpath("run_it001_data.star").write_text("")
    win.widget._update_job_list()
    assert [list_widget.item(i).text() for i in range(list_widget.count())] == ["CtfFind/job003/", "Class3D/job003/"]
    list_widget.setCurrentRow(list_widget.count() - 1)
    with choose_one_dialog_response(himena_ui, True):
        win.widget._clear_trash(join=True)
    win.widget._update_job_list()
    assert list_widget.count() == 0
