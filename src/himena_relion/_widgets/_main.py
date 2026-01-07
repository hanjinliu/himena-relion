from __future__ import annotations
from pathlib import Path
from typing import Callable, Iterator, TypeVar
import logging
import weakref

from qtpy import QtWidgets as QtW, QtCore
from superqt.utils import thread_worker, GeneratorWorker
from watchfiles import watch
from timeit import default_timer
from himena import MainWindow, WidgetDataModel
from himena.plugins import validate_protocol
from himena.qt import QColoredToolButton
from himena_relion import _job_dir, _utils
from himena_relion._widgets._job_widgets import (
    JobWidgetBase,
    QJobStateLabel,
    QRunOutErrLog,
    QNoteEdit,
    QJobPipelineViewer,
    QJobParameterView,
)
from himena_relion._widgets._misc import spacer_widget

_LOGGER = logging.getLogger(__name__)


class QRelionJobWidget(QtW.QWidget):
    job_updated = QtCore.Signal(Path)
    _instances = set["QRelionJobWidget"]()

    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui_ref = weakref.ref(ui)
        self._job_dir: _job_dir.JobDirectory | None = None
        self._control_widget: QRelionJobWidgetControl | None = None
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._state_widget = QJobStateLabel(self)
        layout.addWidget(self._state_widget)
        self._tab_widget = QtW.QTabWidget(self)
        layout.addWidget(self._tab_widget)
        self._watcher: GeneratorWorker | None = None
        self.job_updated.connect(self._on_job_updated)
        self._instances.add(self)

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        """Update the widget with a new model."""
        self._tab_widget.clear()
        if self._watcher:
            self._watcher.quit()
        self._job_dir = job_dir = model.value
        if not isinstance(job_dir, _job_dir.JobDirectory):
            raise TypeError(f"Expected JobDirectory, got {type(job_dir)}")
        self._watcher = self._watch_job_directory(job_dir.path)

        if wcls := RelionJobViewRegistry.instance().get_widget_class(job_dir):
            _LOGGER.info(f"Adding job widget for {job_dir.path}: {wcls!r}")
            wdt = wcls(job_dir)
            self.add_job_widget(wdt)

        self.add_job_widget(QJobPipelineViewer())
        self.add_job_widget(QJobParameterView())
        self.add_job_widget(QRunOutErrLog())
        self.add_job_widget(QNoteEdit())
        for wdt in self._iter_job_widgets():
            try:
                t0 = default_timer()
                wdt.initialize(job_dir)
            except Exception:
                _LOGGER.error(
                    f"Failed to initialize job widget {type(wdt).__name__!r}",
                    exc_info=True,
                )
            else:
                t1 = default_timer()
                _LOGGER.info(
                    f"Initialization of {type(wdt).__name__} took {t1 - t0:.3f} seconds"
                )

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
    def theme_changed_callback(self, theme):
        """Callback when the application theme is changed."""
        for wdt in self.control_widget()._tool_buttons:
            wdt.update_theme(theme)

    @validate_protocol
    def control_widget(self) -> QRelionJobWidgetControl:
        """Get the control widget for this job widget."""
        if self._control_widget is None:
            self._control_widget = QRelionJobWidgetControl(self)
        return self._control_widget

    @validate_protocol
    def widget_added_callback(self):
        """Callback when the widget is added to the main window."""
        for wdt in self._iter_job_widgets():
            wdt.widget_added_callback()

    @validate_protocol
    def widget_closed_callback(self):
        """Callback when the widget is closed."""
        if self._watcher is not None:
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
        if not self._job_dir.path.exists():
            self.widget_closed_callback()
            raise RuntimeError(
                "Job directory has been deleted externally. This widget will no longer "
                "respond to changes. Please close this job widget."
            )
        for wdt in self._iter_job_widgets():
            wdt.on_job_updated(self._job_dir, Path(path))

    def _iter_job_widgets(self) -> Iterator[JobWidgetBase]:
        """Iterate over all job widgets in the tab widget."""
        yield self._state_widget
        for i in range(self._tab_widget.count()):
            if isinstance(wdt := self._tab_widget.widget(i), JobWidgetBase):
                yield wdt


class RelionJobViewRegistry:
    _instance = None

    def __init__(self):
        self._registered_spa = {}
        self._registered_tomo = {}

    @classmethod
    def instance(cls) -> RelionJobViewRegistry:
        """Get the singleton instance of the registry."""
        if cls._instance is None:
            cls._instance = RelionJobViewRegistry()
        return cls._instance

    def get_widget_class(
        self, job_dir: _job_dir.JobDirectory
    ) -> Callable[[_job_dir.JobDirectory], JobWidgetBase] | None:
        """Get the widget class for a specific job type."""
        label = job_dir.job_type_label()
        if job_dir.is_tomo():
            registries = [self._registered_tomo, self._registered_spa]
        else:
            registries = [self._registered_spa, self._registered_tomo]

        # split by `.` and try each part
        for reg in registries:
            num_substrings = label.count(".") + 1
            for i in range(label.count(".")):
                label_sub = ".".join(label.split(".")[: num_substrings - i])
                if factory := reg.get(label_sub, None):
                    return factory


_T = TypeVar("_T", bound=JobWidgetBase)


def register_job(
    job_type: type[_job_dir.JobDirectory] | str,
    is_tomo: bool = False,
) -> Callable[[_T], _T]:
    """Decorator to register a widget class for a specific job type."""
    if isinstance(job_type, type):
        job_type_label = str(job_type._job_type)
    else:
        job_type_label = job_type

    def inner(widget_cls: _T) -> _T:
        ins = RelionJobViewRegistry.instance()
        if is_tomo:
            ins._registered_tomo[job_type_label] = widget_cls
        else:
            ins._registered_spa[job_type_label] = widget_cls
        return widget_cls

    return inner


class QRelionJobWidgetControl(QtW.QWidget):
    def __init__(self, parent: QRelionJobWidget):
        super().__init__()
        self.widget = parent
        self._tool_buttons = [
            QColoredToolButton(self.refresh_widget, _utils.path_icon_svg("refresh")),
        ]
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(spacer_widget())
        for btn in self._tool_buttons:
            layout.addWidget(btn)

    def refresh_widget(self):
        """Reopen this RELION job."""
        self.widget.update_model(self.widget.to_model())
