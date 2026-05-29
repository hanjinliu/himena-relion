from himena import MainWindow
from himena.testing import choose_one_dialog_response
from himena_relion._job_dir import JobDirectory
from himena_relion._widgets._trash_widget import QTrashWidget, _copy_job_paths, _delete_permanently
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

def test_trash_widget(himena_ui: MainWindow, tmpdir):
    rln_dir = prep_relion_project(tmpdir)
    himena_ui.read_file(rln_dir / "default_pipeline.star")
    with choose_one_dialog_response(himena_ui, True):
        trash_job(himena_ui, JobDirectory(rln_dir / "MotionCorr/job002"))
    win = himena_ui.read_file(rln_dir / "Trash")
    assert isinstance(win.widget, QTrashWidget)
    assert win.widget.trash_dir() == rln_dir / "Trash"

    win.widget._make_context_menu()
    win.widget._job_list_widget.setCurrentRow(0)
    win.widget._make_context_menu()

    _copy_job_paths(["MotionCorr/job002/"], rln_dir / "Trash")
    assert (rln_dir / "Trash" / "MotionCorr/job002").exists()
    with choose_one_dialog_response(himena_ui, True):
        _delete_permanently(["MotionCorr/job002/"], rln_dir / "Trash")
    assert not (rln_dir / "Trash" / "MotionCorr/job002").exists()
