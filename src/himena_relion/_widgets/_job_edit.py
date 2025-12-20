from __future__ import annotations
from abc import ABC, abstractmethod
from collections import defaultdict
import logging
from typing import Any

from himena import MainWindow
from qtpy import QtWidgets as QtW, QtCore
from himena.qt import magicgui as _mgui
from himena_relion import _job
from himena_relion._job_class import (
    RelionJob,
    RelionJobExecution,
    parse_string,
    _RelionBuiltinJob,
)
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
        self._job_param_widget = QJobParameter()
        self._exec_btn = QtW.QPushButton("Run Job")  # TODO: support scheduling
        self._exec_btn.clicked.connect(self._exec_action)
        self._mode: Mode = ScheduleMode()

        # TODO: preview button. Visibility of this button needs to be controlled based
        # on whether job edit mode is active.
        # button_layout = QtW.QHBoxLayout()
        # btn = QtW.QPushButton("Preview job.star")
        # btn.setFixedWidth(90)
        # btn.clicked.connect(self.preview_job_star)
        # button_layout.addWidget(btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._title_label)
        # layout.addLayout(button_layout)
        layout.addWidget(self._job_param_widget)
        layout.addWidget(self._exec_btn)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(320, 600)

    def _set_content(self, job_cls: type[RelionJob] | None, title: str):
        self._current_job_cls = job_cls
        self._title_label.setText(f"<b><span style='color: gray;'>{title}</span></b>")
        self._job_param_widget.clear_content()

    def clear_content(self):
        self._set_content(None, "No job selected")

    def update_by_job(self, job_cls: type[RelionJob]):
        """Update the widget based on the job directory."""
        prefix = "Job: "
        self._set_content(job_cls, prefix + job_cls.job_title())
        self._job_param_widget.update_by_job(job_cls)

    def set_parameters(self, params: dict):
        if (job_cls := self._current_job_cls) is None:
            raise RuntimeError("No job class selected.")
        if issubclass(job_cls, _RelionBuiltinJob):
            params = job_cls.normalize_kwargs_inv(**params)
        self._job_param_widget.set_parameters(params)

    def get_parameters(self) -> dict[str, Any]:
        """Get the parameters from the widgets."""
        if self._current_job_cls is None:
            raise RuntimeError("No job class selected.")
        return self._job_param_widget.get_parameters()

    def set_schedule_mode(self):
        self._set_mode(ScheduleMode())

    def set_edit_mode(self, job_dir: _job.JobDirectory):
        self._set_mode(EditMode(job_dir))

    # def preview_job_star(self):
    #     """Preview the job star file based on current parameters."""
    #     if self._current_job_cls is None:
    #         raise RuntimeError("No job class selected.")
    #     params = self.get_parameters()
    #     job_star_df = self._current_job_cls.prep_job_star(**params)
    #     buf = StringIO()
    #     starfile.write(job_star_df, buf)
    #     self._ui.add_object(buf.getvalue(), type="text", title="Preview job.star")

    def _set_mode(self, mode: Mode):
        self._mode = mode
        self._exec_btn.setText(mode.button_text())

    def _exec_action(self):
        self._mode.exec(self)


class QJobParameter(QtW.QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self._scroll_area_inner = QtW.QWidget()
        self.setWidget(self._scroll_area_inner)
        self._param_layout = QtW.QVBoxLayout(self._scroll_area_inner)
        self._param_layout.setContentsMargins(0, 0, 0, 0)
        self._mgui_widgets: list[ValueWidget] = []
        self._groupboxes: list[QtW.QGroupBox] = []

    def clear_content(self):
        for groupbox in self._groupboxes:
            self._param_layout.removeWidget(groupbox)
            groupbox.deleteLater()
        self._mgui_widgets.clear()
        self._groupboxes.clear()

    def update_by_job(self, job_cls: type[RelionJob]):
        """Update the widget based on the job directory."""
        self.clear_content()

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

    def set_parameters(self, params: dict, enabled: bool = True):
        # NOTE: params must be normalized already
        params = params.copy()
        for widget in self._mgui_widgets:
            if widget.name in params:
                new_value = params.pop(widget.name)
                widget.value = parse_string(new_value, widget.annotation)
            widget.enabled = enabled
        if params:
            _LOGGER.warning(
                f"Parameters not found in job directory: {list(params.keys())}"
            )

    def get_parameters(self) -> dict[str, Any]:
        """Get the parameters from the widgets."""
        params = {}
        for widget in self._mgui_widgets:
            params[widget.name] = widget.value
        return params


class Mode(ABC):
    @abstractmethod
    def exec(self, widget: QJobScheduler):
        """Execute the mode action."""

    @abstractmethod
    def button_text(self) -> str:
        """Get the button text for this mode."""


class ScheduleMode(Mode):
    def exec(self, widget: QJobScheduler):
        if (job_cls := widget._current_job_cls) is None:
            raise RuntimeError("No job class selected.")
        params = widget.get_parameters()
        proc = job_cls.create_and_run_job(**params)
        widget.clear_content()
        if isinstance(proc, RelionJobExecution):
            widget._ui.read_file(proc.job_directory.path)
            widget._ui.show_notification(f"Job '{job_cls.job_title()}' launched.")

    def button_text(self) -> str:
        return "Run Job"


class EditMode(Mode):
    def __init__(self, job_dir: _job.JobDirectory):
        self.job_dir = job_dir

    def exec(self, widget: QJobScheduler):
        if widget._current_job_cls is None:
            raise RuntimeError("No job class selected.")
        job_cls = widget._current_job_cls
        job = job_cls(self.job_dir)
        # Delete all the non needed files
        self.job_dir.clear_job()
        # Update the scheduler widget with the parameters used to run this job
        params = widget.get_parameters()
        job.edit_and_run_job(**params)
        widget.clear_content()
        widget._ui.show_notification(f"Job '{job_cls.job_title()}' edited and rerun.")

    def button_text(self) -> str:
        return "Overwrite And Run"
