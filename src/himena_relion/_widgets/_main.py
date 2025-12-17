from __future__ import annotations
from pathlib import Path
import subprocess
from typing import Callable, Iterator, TypeVar
import logging
import weakref

from qtpy import QtWidgets as QtW, QtCore
from superqt.utils import thread_worker, GeneratorWorker
from watchfiles import watch

from himena import MainWindow, WidgetDataModel
from himena.plugins import validate_protocol
from himena_builtins.qt.widgets._shared import spacer_widget
from himena_relion import _job
from himena_relion._widgets._job_widgets import (
    JobWidgetBase,
    QJobStateLabel,
    QRunErrLog,
    QRunOutLog,
    QNoteLog,
    QJobInOut,
)
from himena_relion.consts import FileNames

_LOGGER = logging.getLogger(__name__)


class QRelionJobWidget(QtW.QWidget):
    job_updated = QtCore.Signal(Path)
    _instances = set["QRelionJobWidget"]()

    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui_ref = weakref.ref(ui)
        self._job_dir: _job.JobDirectory | None = None
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._state_widget = QJobStateLabel()
        layout.addWidget(self._state_widget)
        self._tab_widget = QtW.QTabWidget(self)
        layout.addWidget(self._tab_widget)
        self._watcher: GeneratorWorker | None = None
        self.job_updated.connect(self._on_job_updated)
        self._control: QRelionJobControl | None = None
        self._instances.add(self)

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        """Update the widget with a new model."""
        self._tab_widget.clear()
        if self._watcher:
            self._watcher.quit()
        self._job_dir = job_dir = model.value
        if not isinstance(job_dir, _job.JobDirectory):
            raise TypeError(f"Expected JobDirectory, got {type(job_dir)}")
        self._watcher = self._watch_job_directory(job_dir.path)

        if wcls := RelionJobViewRegistry.instance().get_widget_class(type(job_dir)):
            _LOGGER.info(f"Adding job widget for {job_dir.path}: {wcls!r}")
            wdt = wcls()
            self.add_job_widget(wdt)

        self.add_job_widget(QJobInOut())
        self.add_job_widget(QRunOutLog())
        self.add_job_widget(QRunErrLog())
        self.add_job_widget(QNoteLog())
        try:
            self._state_widget.initialize(job_dir)
        except Exception as e:
            _LOGGER.error(f"Failed to initialize job state widget: {e!r}")
        for wdt in self._iter_job_widgets():
            try:
                wdt.initialize(job_dir)
            except Exception as e:
                _LOGGER.error(f"Failed to initialize job widget {wdt!r}: {e!r}")
        if control := self._control:
            control._set_abort_enabled(job_dir.can_abort())

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        """Convert the widget state back to a model."""
        if self._job_dir is None:
            raise RuntimeError("Job directory is not set.")
        return WidgetDataModel(
            value=self._job_dir,
            type=self._job_dir.himena_model_type(),
        )

    @validate_protocol
    def model_type(self) -> str:
        return self._job_dir.himena_model_type()

    @validate_protocol
    def size_hint(self):
        return 420, 540

    @validate_protocol
    def control_widget(self) -> QRelionJobControl | None:
        """Return the control widget for the job."""
        if self._control is None:
            self._control = QRelionJobControl(self)
            if self._job_dir is not None:
                self._control._set_abort_enabled(self._job_dir.can_abort())
        return self._control

    @validate_protocol
    def widget_closed_callback(self):
        """Callback when the widget is closed."""
        self._watcher.quit()
        self._watcher = None

    def add_job_widget(self, widget: JobWidgetBase):
        """Add a job widget to the tab widget."""
        if not isinstance(widget, JobWidgetBase):
            raise TypeError(f"Expected JobWidgetBase, got {type(widget)}")
        self._tab_widget.addTab(widget, widget.tab_title())

    @thread_worker(start_thread=True)
    def _watch_job_directory(self, path: Path):
        """Watch the job directory for changes."""
        for changes in watch(path, rust_timeout=400, yield_on_timeout=True):
            if self._watcher is None:
                return  # stopped
            for change, fp in changes:
                self.job_updated.emit(Path(fp))
            yield

    def _on_job_updated(self, path: Path):
        """Handle changes to the job directory."""
        if self._job_dir is None:
            return
        if path.stem.startswith("RELION_JOB_"):
            self._state_widget.on_job_updated(self._job_dir, path)
            if control := self._control:
                control._set_abort_enabled(self._job_dir.can_abort())
        else:
            for wdt in self._iter_job_widgets():
                wdt.on_job_updated(self._job_dir, Path(path))

    def _iter_job_widgets(self) -> Iterator[JobWidgetBase]:
        """Iterate over all job widgets in the tab widget."""
        for i in range(self._tab_widget.count()):
            if isinstance(wdt := self._tab_widget.widget(i), JobWidgetBase):
                yield wdt


class RelionJobViewRegistry:
    _instance = None

    def __init__(self):
        self._registered = {}

    @classmethod
    def instance(cls) -> RelionJobViewRegistry:
        """Get the singleton instance of the registry."""
        if cls._instance is None:
            cls._instance = RelionJobViewRegistry()
        return cls._instance

    def register(
        self,
        job_type: type[_job.JobDirectory],
        widget_cls: type[JobWidgetBase],
    ):
        """Register a widget class for a specific job type."""
        if not issubclass(widget_cls, JobWidgetBase):
            raise TypeError(
                f"Widget class must be a subclass of JobWidgetBase, got {widget_cls}"
            )
        self._registered[job_type] = widget_cls

    def get_widget_class(
        self, job_type: type[_job.JobDirectory]
    ) -> type[JobWidgetBase] | None:
        """Get the widget class for a specific job type."""
        return self._registered.get(job_type, None)


_T = TypeVar("_T", bound=JobWidgetBase)


def register_job(job_type: type[_job.JobDirectory]) -> Callable[[_T], _T]:
    """Decorator to register a widget class for a specific job type."""

    def inner(widget_cls: _T) -> _T:
        if not issubclass(widget_cls, JobWidgetBase):
            raise TypeError(
                f"Widget class must be a subclass of JobWidgetBase, got {widget_cls}"
            )
        RelionJobViewRegistry.instance().register(job_type, widget_cls)
        return widget_cls

    return inner


class QRelionJobControl(QtW.QWidget):
    """Control widget for QRelionJobWidget."""

    def __init__(self, job_widget: QRelionJobWidget):
        super().__init__()
        self._job_widget = job_widget
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._clear_button = QtW.QPushButton("Clear Job")
        self._edit_button = QtW.QPushButton("Edit Job")
        self._abort_button = QtW.QPushButton("Abort Job")

        self._clear_button.clicked.connect(self._on_clear_clicked)
        self._edit_button.clicked.connect(self.on_edit_clicked)
        self._abort_button.clicked.connect(self._on_abort_clicked)

        layout.addWidget(spacer_widget())
        layout.addWidget(self._clear_button)
        layout.addWidget(self._edit_button)
        layout.addWidget(self._abort_button)

    def _on_abort_clicked(self):
        if job_dir := self._job_widget._job_dir:
            if job_dir.state() == _job.RelionJobState.EXIT_SUCCESS:
                raise RuntimeError("Cannot abort a finished job.")
            job_dir.path.joinpath(FileNames.ABORT_NOW).touch()

    def _set_abort_enabled(self, enabled: bool):
        self._abort_button.setEnabled(enabled)

    def on_edit_clicked(self):
        if job_dir := self._job_widget._job_dir:
            for state_file in job_dir.path.glob("RELION_JOB_*"):
                if state_file.exists():
                    state_file.unlink()
            if ui := self._job_widget._ui_ref():
                job_cls = job_dir._to_job_class()
                if job_cls is None:
                    raise RuntimeError("Cannot determine job class.")
                scheduler = job_cls._show_scheduler_widget(ui, {})
                scheduler.set_edit_mode(job_dir)
                scheduler.set_parameters(job_dir.get_job_params_as_dict())

    def _on_clear_clicked(self):
        if job_dir := self._job_widget._job_dir:
            subprocess.run(
                ["relion_pipeliner", "--harsh_clean", str(int(job_dir.job_id))]
            )
