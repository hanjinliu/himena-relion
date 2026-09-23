from pathlib import Path
import shutil
from cmap import Color
import pytest
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt, QModelIndex
from pytestqt.qtbot import QtBot
from himena import MainWindow
from himena.testing import file_dialog_response
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
    out._on_wordwrap_changed(True)
    out._on_wordwrap_changed(False)

def test_pipeline_viewer(qtbot: QtBot, tmpdir):
    _job_dir = Path(tmpdir, "job001")
    _job_dir.mkdir()
    pipeline_file = _job_dir.joinpath("job_pipeline.star")
    pipeline_file.write_text(read_sample_job_pipeline_star("refine3d.star"))
    viewer = QJobPipelineViewer(show_tree_view=True)
    qtbot.addWidget(viewer)
    job_dir_obj = JobDirectory(_job_dir)
    viewer.initialize(job_dir_obj)
    viewer.on_job_updated(job_dir_obj, _job_dir / "job_pipeline.star")
    viewer._tree_view.initialize(job_dir_obj)
    viewer._tree_view._make_context_menu(viewer._tree_view.model().index(0, 0))
    viewer._tree_view._make_drag(viewer._tree_view.model().index(0, 0))

def test_directory_tree_view_wsl(qtbot: QtBot, tmpdir, monkeypatch: pytest.MonkeyPatch):
    from himena_relion._widgets import _job_widgets
    from himena_relion._widgets._scandir_model import QScandirModel

    _job_dir = Path(tmpdir, "job001")
    _job_dir.mkdir()
    _job_dir.joinpath("job_pipeline.star").write_text(
        read_sample_job_pipeline_star("refine3d.star")
    )
    _job_dir.joinpath("run.out").write_text("out")
    _job_dir.joinpath("sub").mkdir()
    _job_dir.joinpath("sub", "a.star").write_text("")
    monkeypatch.setattr(_job_widgets, "is_wsl_path", lambda path: True)

    viewer = QJobPipelineViewer(show_tree_view=True)
    qtbot.addWidget(viewer)
    job_dir_obj = JobDirectory(_job_dir)
    viewer.initialize(job_dir_obj)
    tree = viewer._tree_view
    model = tree.model()
    assert isinstance(model, QScandirModel)

    def names(parent=None):
        parent = QModelIndex() if parent is None else parent
        return [
            model.data(model.index(i, 0, parent))
            for i in range(model.rowCount(parent))
        ]

    # directories first
    assert names() == ["sub", "job_pipeline.star", "run.out"]
    sub_index = model.index(0, 0)
    assert model.hasChildren(sub_index)
    assert model.rowCount(sub_index) == 0  # not scanned yet
    assert model.canFetchMore(sub_index)
    model.fetchMore(sub_index)
    assert names(sub_index) == ["a.star"]
    assert Path(model.filePath(model.index(0, 0, sub_index))) == _job_dir / "sub" / "a.star"
    assert model.parent(model.index(0, 0, sub_index)) == sub_index

    # file added/removed
    _job_dir.joinpath("run.err").write_text("err")
    _job_dir.joinpath("run.out").unlink()
    viewer.on_job_updated(job_dir_obj, _job_dir / "run.err")
    assert names() == ["sub", "job_pipeline.star", "run.err"]
    _job_dir.joinpath("sub", "b.star").write_text("")
    viewer.on_job_updated(job_dir_obj, _job_dir / "sub" / "b.star")
    assert names(model.index(0, 0)) == ["a.star", "b.star"]

    tree._make_context_menu(model.index(1, 0))
    tree._make_drag(model.index(1, 0))
    assert "Size:" in model.data(model.index(1, 0), Qt.ItemDataRole.ToolTipRole)

def test_flowchart(himena_ui: MainWindow, qtbot: QtBot, tmpdir):
    from himena_relion.pipeline.widgets import QRelionPipelineFlowChart, _make_tag_icon

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
    flow_chart._prep_right_click_menu(qitem.item())

    # tags
    _make_tag_icon(Color("red"), checked=False)
    _make_tag_icon(Color("red"), checked=True)
    pipeline = flow_chart._pipeline()
    flow_chart._flow_chart.read_gui_state(pipeline)
    flow_chart._flow_chart.save_gui_state(pipeline)

def test_path_input(himena_ui: MainWindow, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch):
    from himena_relion._widgets._path_input import QPathDropWidget, PathDrop

    widget = PathDrop("", type_label=["DensityMap"])
    qwidget: QPathDropWidget = widget.native
    rln_dir = Path(__file__).parent
    monkeypatch.setattr(qwidget, "get_relion_directory", lambda: rln_dir)
    qtbot.addWidget(qwidget)

    assert isinstance(qwidget._make_menu(), QtW.QMenu)
    with file_dialog_response(himena_ui, rln_dir / "__init__.py"):
        qwidget._on_browse_clicked()
    assert qwidget.value() == "__init__.py"
    qwidget._open_path()
    widget.set_value("*.py")
    qwidget._glob_paths()
