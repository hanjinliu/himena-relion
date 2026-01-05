from himena import MainWindow
from himena.plugins import when_reader_used
from himena.workflow import LocalReaderMethod
from himena_relion._job_dir import JobDirectory
from himena_relion.consts import Type
from ._utils import JOBS_DIR_SPA

def _iter_execute_suggestion(ui: MainWindow, path):
    job_dir = JobDirectory(path)
    pre = job_dir._to_job_class()
    type_pre = Type.RELION_JOB + "." + pre.himena_model_type()
    reg = when_reader_used(type_pre)._registry
    meth = LocalReaderMethod(output_model_type=type_pre, path=job_dir.path)
    ui.read_file(path)
    for suggest in reg.iter_suggestion(type_pre, meth):
        suggest.execute(ui, meth)

def test_initial_model_to_refine(himena_ui):
    _iter_execute_suggestion(himena_ui, JOBS_DIR_SPA / "InitialModel" / "job001")
    _iter_execute_suggestion(himena_ui, JOBS_DIR_SPA / "Class3D" / "job001")
    _iter_execute_suggestion(himena_ui, JOBS_DIR_SPA / "Class3D" / "job002")
    _iter_execute_suggestion(himena_ui, JOBS_DIR_SPA / "Refine3D" / "job001")
