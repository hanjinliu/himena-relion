from __future__ import annotations
import logging
from qtpy import QtWidgets as QtW
from himena_relion._widgets._job_widgets import JobWidgetBase
from himena_relion import _job
from himena_relion.external import pick_job_class

_LOGGER = logging.getLogger(__name__)


class QExternalJobView(QtW.QScrollArea, JobWidgetBase):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)

    def on_job_updated(self, job_dir: _job.ExternalJobDirectory, path: str):
        """Handle changes to the job directory."""
        if widget := self.widget():
            if hasattr(widget, "on_job_updated"):
                widget.on_job_updated(job_dir, path)

    def initialize(self, job_dir: _job.ExternalJobDirectory):
        """Initialize the viewer with the job directory."""
        fn_exe = job_dir.get_job_param("fn_exe")
        if fn_exe.startswith("himena-relion "):
            import_path = fn_exe[len("himena-relion ") :].strip()
            if job_cls := pick_job_class(import_path):
                external_job = job_cls(job_dir)
                # set widget
                widget = external_job.provide_widget(job_dir)
                if widget is not NotImplemented:
                    self.setWidget(widget)
                    return
        self.setWidget(QtW.QLabel("No widget is implemented for this external job."))
