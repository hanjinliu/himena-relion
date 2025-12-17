from __future__ import annotations
from abc import ABC, abstractmethod
from collections import defaultdict
import shutil
import logging
from typing import Any

from himena import MainWindow
from qtpy import QtWidgets as QtW, QtCore
from himena.qt import magicgui as _mgui
from himena_relion import _job
from himena_relion._job_class import RelionJob, parse_string, _RelionBuiltinJob
from magicgui.widgets.bases import ValueWidget
from magicgui.signature import MagicParameter

_LOGGER = logging.getLogger(__name__)


# TODO: copy/paste
class QJobScheduler(QtW.QWidget):
    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui = ui
        layout = QtW.QVBoxLayout(self)
        self._title_label = QtW.QLabel("")  # job name
        font = self._title_label.font()
        font.setPointSize(font.pointSize() + 3)
        self._title_label.setFont(font)
        layout.addWidget(self._title_label)
        self._scroll_area = QtW.QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        layout.addWidget(self._scroll_area)
        self._scroll_area_inner = QtW.QWidget()
        self._scroll_area.setWidget(self._scroll_area_inner)
        self._param_layout = QtW.QVBoxLayout(self._scroll_area_inner)
        self._param_layout.setContentsMargins(0, 0, 0, 0)
        self._exec_btn = QtW.QPushButton("Run Job")  # TODO: support scheduling
        layout.addWidget(self._exec_btn)
        self._current_job_cls: type[RelionJob] | None = None
        self._mgui_widgets: list[ValueWidget] = []
        self._groupboxes: list[QtW.QGroupBox] = []
        self._exec_btn.clicked.connect(self._exec_action)
        self._mode: Mode = ScheduleMode()

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(320, 600)

    def _set_content(self, job_cls: type[RelionJob] | None, title: str):
        self._current_job_cls = job_cls
        self._title_label.setText(f"<b><span style='color: gray;'>{title}</span></b>")
        for groupbox in self._groupboxes:
            self._param_layout.removeWidget(groupbox)
            groupbox.deleteLater()
        self._mgui_widgets.clear()
        self._groupboxes.clear()

    def clear_content(self):
        self._set_content(None, "No job selected")

    def update_by_job(self, job_cls: type[RelionJob]):
        """Update the widget based on the job directory."""
        self._set_content(job_cls, job_cls.job_title())

        sig = job_cls._signature()
        typemap = _mgui.get_type_map()
        groups = defaultdict[str, list[ValueWidget]](list)
        for param in sig.parameters.values():
            param = MagicParameter.from_parameter(param)
            group = param.options.pop("group", "Parameters")
            widget = param.to_widget(type_map=typemap)
            groups[group].append(widget)
        for group, widgets in groups.items():
            gb = QtW.QGroupBox(group)
            fontsize = gb.font().pointSize() + 2
            gb.setStyleSheet(f"QGroupBox::title {{ font-size: {fontsize}pt; }}")
            gb_layout = QtW.QVBoxLayout(gb)
            gb_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            for widget in widgets:
                param_label = QtW.QLabel(f"<b>{widget.label}</b>")
                gb_layout.addWidget(param_label)
                if isinstance(widget, _mgui.ToggleSwitch):
                    widget.text = ""
                elif isinstance(widget, (_mgui.IntEdit, _mgui.FloatEdit)):
                    widget.max_width = 160
                gb_layout.addWidget(widget.native)
                param_label.setToolTip(widget.tooltip)
                self._mgui_widgets.append(widget)
            self._param_layout.addWidget(gb)
            self._groupboxes.append(gb)

    def set_parameters(self, params: dict):
        params = params.copy()
        if (job_cls := self._current_job_cls) is None:
            raise RuntimeError("No job class selected.")
        if issubclass(job_cls, _RelionBuiltinJob):
            params = job_cls.normalize_kwargs_inv(**params)
        for widget in self._mgui_widgets:
            if widget.name in params:
                new_value = params.pop(widget.name)
                widget.value = parse_string(new_value, widget.annotation)
        if params:
            _LOGGER.warning(
                f"Parameters not found in job directory: {list(params.keys())}"
            )

    def get_parameters(self) -> dict[str, Any]:
        """Get the parameters from the widgets."""
        if self._current_job_cls is None:
            raise RuntimeError("No job class selected.")
        params = {}
        for widget in self._mgui_widgets:
            params[widget.name] = widget.value
        return params

    def set_schedule_mode(self):
        self._set_mode(ScheduleMode())

    def set_edit_mode(self, job_dir: _job.JobDirectory):
        self._set_mode(EditMode(job_dir))

    def _set_mode(self, mode: Mode):
        self._mode = mode
        self._exec_btn.setText(mode.button_text())

    def _exec_action(self):
        self._mode.exec(self)


class Mode(ABC):
    @abstractmethod
    def exec(self, widget: QJobScheduler):
        """Execute the mode action."""

    @abstractmethod
    def button_text(self) -> str:
        """Get the button text for this mode."""


class ScheduleMode(Mode):
    def exec(self, widget: QJobScheduler):
        if widget._current_job_cls is None:
            raise RuntimeError("No job class selected.")
        params = widget.get_parameters()
        proc = widget._current_job_cls.create_and_run_job(**params)
        widget.clear_content()
        widget._ui.read_file(proc.job_directory)

    def button_text(self) -> str:
        return "Run Job"


class EditMode(Mode):
    def __init__(self, job_dir: _job.JobDirectory):
        self.job_dir = job_dir

    def exec(self, widget: QJobScheduler):
        if widget._current_job_cls is None:
            raise RuntimeError("No job class selected.")
        job_cls = widget._current_job_cls
        # Delete all the non needed files
        for item in self.job_dir.path.iterdir():
            if item.is_file():
                if item.name not in MINIMUM_FILES_TO_KEEP:
                    item.unlink()
            else:
                shutil.rmtree(item)

        # Update the scheduler widget with the parameters used to run this job
        params = widget.get_parameters()
        job_cls(self.job_dir).edit_and_run_job(**params)
        widget.clear_content()

    def button_text(self) -> str:
        return "Overwrite And Run"


MINIMUM_FILES_TO_KEEP = ["job.star", "job_pipeline.star", "note.txt"]
