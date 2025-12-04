from __future__ import annotations
from pathlib import Path
from typing import Callable, Iterator, TypeVar
import logging

from himena import WidgetDataModel
from qtpy import QtWidgets as QtW, QtCore
from superqt.utils import thread_worker, GeneratorWorker
from watchfiles import watch

from himena.plugins import validate_protocol
from himena_relion import _job
from himena_relion._widgets._job_widgets import (
    JobWidgetBase,
    QJobStateLabel,
    QRunErrLog,
    QRunOutLog,
    QNoteLog,
    QJobInputs,
    QJobOutputs,
)
from himena_relion.consts import Type

_LOGGER = logging.getLogger(__name__)


class QRelionJobWidget(QtW.QWidget):
    job_updated = QtCore.Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._job_dir: _job.JobDirectory | None = None
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._state_widget = QJobStateLabel()
        layout.addWidget(self._state_widget)
        self._tab_widget = QtW.QTabWidget(self)
        layout.addWidget(self._tab_widget)
        self._watcher: GeneratorWorker | None = None
        self.job_updated.connect(self._on_job_updated)

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

        self.add_job_widget(QJobInputs())
        self.add_job_widget(QJobOutputs())
        self.add_job_widget(QRunOutLog())
        self.add_job_widget(QRunErrLog())
        self.add_job_widget(QNoteLog())
        self._state_widget.initialize(job_dir)
        for wdt in self._iter_job_widgets():
            wdt.initialize(job_dir)

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        """Convert the widget state back to a model."""
        if self._job_dir is None:
            raise RuntimeError("Job directory is not set.")
        return WidgetDataModel(
            value=self._job_dir,
            type=Type.RELION_JOB,
        )

    @validate_protocol
    def size_hint(self):
        return 370, 420

    @validate_protocol
    def widget_closed_callback(self):
        """Callback when the widget is closed."""
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
            return
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
