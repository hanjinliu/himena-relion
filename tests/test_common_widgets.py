from pathlib import Path
import shutil
from pytestqt.qtbot import QtBot
from himena import MainWindow
from himena_relion._widgets._job_widgets import QNoteEdit, QRunOutLog, QRunErrLog, QJobPipelineViewer
from himena_relion._job_dir import JobDirectory
from ._utils import read_sample_job_pipeline_star, JOBS_DIR_SPA

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

def test_flowchart(himena_ui: MainWindow, qtbot: QtBot, tmpdir):
    from himena_relion.pipeline.widgets import QRelionPipelineFlowChart

    _proj_dir = Path(tmpdir)
    shutil.copytree(JOBS_DIR_SPA / "Import", _proj_dir / "Import")
    default_pipeline_star_content = (
        "data_pipeline_general\n"
        "_rlnPipeLineJobCounter 2\n"
        "\n"
        "data_pipeline_processes\n"
        "loop_\n"
        "_rlnPipeLineProcessName #1\n"
        "_rlnPipeLineProcessAlias #2\n"
        "_rlnPipeLineProcessTypeLabel #3\n"
        "_rlnPipeLineProcessStatusLabel #4\n"
        "Import/job001/	None	relion.import.movies	Succeeded\n"
        "\n"
        "data_pipeline_nodes\n"
        "loop_\n"
        "_rlnPipeLineNodeName #1\n"
        "_rlnPipeLineNodeTypeLabel #2\n"
        "Import/job001/	relion.import.movies\n"
        "\n"
        "data_pipeline_output_edges\n"
        "loop_\n"
        "_rlnPipeLineEdgeProcess #1\n"
        "_rlnPipeLineEdgeToNode #2\n"
        "Import/job001/	Import/job001/movies.star\n"
    )
    star = _proj_dir / "default_pipeline.star"
    star.write_text(default_pipeline_star_content)
    himena_ui.read_file(star)
    dock = himena_ui.dock_widgets[0]
    assert isinstance(flow_chart := dock.widget, QRelionPipelineFlowChart)
    assert len(flow_chart._flow_chart._node_map) == 1
    qitem = list(flow_chart._flow_chart._node_map.values())[0]
    flow_chart._flow_chart._prep_right_click_menu(qitem.item())
