from pathlib import Path
from pytestqt.qtbot import QtBot
from himena_relion._widgets._job_widgets import QNoteEdit, QRunOutLog, QRunErrLog, QJobPipelineViewer
from himena_relion._job_dir import JobDirectory
from ._utils import read_sample_job_pipeline_star

def test_text_edit(qtbot: QtBot, tmpdir):
    _job_dir = Path(tmpdir, "job001")
    _job_dir.mkdir()
    _job_dir.joinpath("note.txt").write_text("Initial note.")
    _job_dir.joinpath("run.out").write_text("out")
    _job_dir.joinpath("run.err").write_text("err")
    note = QNoteEdit()
    out = QRunOutLog()
    err = QRunErrLog()
    qtbot.addWidget(note)
    qtbot.addWidget(out)
    qtbot.addWidget(err)
    job_dir_obj = JobDirectory(_job_dir)
    note.initialize(job_dir_obj)
    out.initialize(job_dir_obj)
    err.initialize(job_dir_obj)
    note.on_job_updated(job_dir_obj, _job_dir / "note.txt")
    out.on_job_updated(job_dir_obj, _job_dir / "run.out")
    err.on_job_updated(job_dir_obj, _job_dir / "run.err")
    assert note.toPlainText() == "Initial note."
    assert out.toPlainText() == "out"
    assert err.toPlainText() == "err"

def test_pipeline_viewer(qtbot: QtBot, tmpdir):
    _job_dir = Path(tmpdir, "job001")
    _job_dir.mkdir()
    pipeline_file = _job_dir.joinpath("job_pipeline.star")
    pipeline_file.write_text(read_sample_job_pipeline_star("refine3d.star"))
    viewer = QJobPipelineViewer()
    qtbot.addWidget(viewer)
    job_dir_obj = JobDirectory(_job_dir)
    viewer.initialize(job_dir_obj)
    viewer.on_job_updated(job_dir_obj, _job_dir / "job_pipeline.star")
