from __future__ import annotations
from collections import defaultdict
from typing import Any

from himena import MainWindow
from qtpy import QtWidgets as QtW, QtCore
from himena.qt.magicgui import get_type_map
from himena_relion._job_class import RelionJob
from magicgui.widgets.bases import ValueWidget
from magicgui.signature import MagicParameter


class QJobScheduler(QtW.QWidget):
    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui = ui
        layout = QtW.QVBoxLayout(self)
        self._title_label = QtW.QLabel("Job Name")
        layout.addWidget(self._title_label)
        self._scroll_area = QtW.QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        layout.addWidget(self._scroll_area)
        self._scroll_area_inner = QtW.QWidget()
        self._scroll_area.setWidget(self._scroll_area_inner)
        self._param_layout = QtW.QVBoxLayout(self._scroll_area_inner)
        self._param_layout.setContentsMargins(0, 0, 0, 0)
        self._schedule_btn = QtW.QPushButton("Schedule Job")
        layout.addWidget(self._schedule_btn)
        self._current_job_cls: type[RelionJob] | None = None
        self._mgui_widgets: list[ValueWidget] = []
        self._schedule_btn.clicked.connect(self.schedule_current_job)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(320, 600)

    def update_by_job(self, job_cls: type[RelionJob]):
        """Update the widget based on the job directory."""
        self._current_job_cls = job_cls
        self._title_label.setText(
            f"<b><span style='color: gray;'>{job_cls.job_title()}</span></b>"
        )
        for groupbox in self._param_layout.children():
            self._param_layout.removeWidget(groupbox)
            groupbox.deleteLater()
        self._mgui_widgets.clear()

        sig = job_cls._signature()
        typemap = get_type_map()
        groups = defaultdict[str, list[ValueWidget]](list)
        for param in sig.parameters.values():
            # if param
            param = MagicParameter.from_parameter(param)
            group = param.options.pop("group", "Parameters")
            widget = param.to_widget(type_map=typemap)
            groups[group].append(widget)
        for group, widgets in groups.items():
            gb = QtW.QGroupBox(group)
            gb_layout = QtW.QVBoxLayout(gb)
            gb_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            for widget in widgets:
                gb_layout.addWidget(QtW.QLabel(f"<b>{widget.label}</b>"))
                gb_layout.addWidget(widget.native)
                self._mgui_widgets.append(widget)
            self._param_layout.addWidget(gb)

    def get_parameters(self) -> dict[str, Any]:
        """Get the parameters from the widgets."""
        if self._current_job_cls is None:
            raise RuntimeError("No job class selected.")
        params = {}
        for widget in self._mgui_widgets:
            params[widget.name] = widget.value
        return params

    def schedule_current_job(self):
        """Schedule the current job with the parameters."""
        if self._current_job_cls is None:
            raise RuntimeError("No job class selected.")
        params = self.get_parameters()
        d = self._current_job_cls.create_and_run_job(**params)
        self._ui.read_file(d)
