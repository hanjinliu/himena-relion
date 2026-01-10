from __future__ import annotations
from abc import ABC, abstractmethod
from collections import defaultdict
import logging
from typing import Any, Union

from himena import MainWindow
from qtpy import QtWidgets as QtW, QtCore, QtGui
from magicgui.widgets import ComboBox
from himena.qt import magicgui as _mgui, QColoredSVGIcon
from himena_relion import _job_dir, _utils
from himena_relion._job_class import (
    RelionJob,
    RelionJobExecution,
    parse_string,
    _Relion5BuiltinContinue,
)
from magicgui.widgets.bases import ValueWidget
from magicgui.signature import MagicParameter

_LOGGER = logging.getLogger(__name__)


# TODO: copy/paste
class QJobScheduler(QtW.QWidget):
    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui = ui
        self._cwd = None
        layout = QtW.QVBoxLayout(self)
        self._title_label = QtW.QLabel("")  # job name
        font = self._title_label.font()
        font.setPointSize(font.pointSize() + 3)
        self._title_label.setFont(font)
        self._job_param_widget = QJobParameter()
        self._exec_btn = QtW.QPushButton("Run Job")
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
        self._exec_btn.setVisible(False)

    def update_by_job(self, job_cls: type[RelionJob], cwd=None):
        """Update the widget based on the job directory.

        This method does NOT update the parameters; call `set_parameters` after this."""
        if issubclass(job_cls, _Relion5BuiltinContinue):
            prefix = "Continue - "
        else:
            prefix = "Job: "
        self._set_content(job_cls, prefix + job_cls.job_title())
        self._job_param_widget.update_by_job(job_cls)
        self._cwd = cwd

    def set_parameters(self, params: dict):
        if (job_cls := self._current_job_cls) is None:
            raise RuntimeError("No job class selected.")
        params = job_cls.normalize_kwargs_inv(**params)
        self._job_param_widget.set_parameters(params)

    def get_parameters(self) -> dict[str, Any]:
        """Get the parameters from the widgets."""
        if self._current_job_cls is None:
            raise RuntimeError("No job class selected.")
        return self._job_param_widget.get_parameters()

    def set_schedule_mode(self):
        self._set_mode(ScheduleMode())

    def set_continue_mode(self, job_dir: _job_dir.JobDirectory):
        self._set_mode(ContinueMode(job_dir))

    def set_edit_mode(self, job_dir: _job_dir.JobDirectory):
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
        self._exec_btn.setVisible(True)

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
        self._mgui_widgets: dict[str, ValueWidget] = {}
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

        # convert `run` to widgets.
        sig = job_cls._signature()
        typemap = _mgui.get_type_map()
        groups = defaultdict[str, list[ValueWidget]](list)
        tooltip_for_widget: dict[str, str] = {}
        for param in sig.parameters.values():
            param = MagicParameter.from_parameter(param)
            group = param.options.pop("group", "Parameters")
            tooltip = param.options.pop("tooltip", "")
            widget = param.to_widget(type_map=typemap)
            groups[group].append(widget)
            tooltip_for_widget[widget.name] = tooltip
        for group, widgets in groups.items():
            gb = QtW.QGroupBox(group)
            fontsize = gb.font().pointSize() + 3
            gb.setStyleSheet(f"QGroupBox::title {{ font-size: {fontsize}pt; }}")
            gb_layout = QtW.QVBoxLayout(gb)
            gb_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            for widget in widgets:
                param_label = QParameterNameLabel(
                    widget.label, tooltip=tooltip_for_widget.get(widget.name, "")
                )
                gb_layout.addWidget(param_label)
                if isinstance(widget, _mgui.ToggleSwitch):
                    widget.text = ""
                elif isinstance(widget, (_mgui.IntEdit, _mgui.FloatEdit, ComboBox)):
                    widget.max_width = 200
                gb_layout.addWidget(widget.native)
                self._mgui_widgets[widget.name] = widget
            self._param_layout.addWidget(gb)
            self._groupboxes.append(gb)
        # initialize widgets
        job_cls.setup_widgets(self._mgui_widgets)

    def set_parameters(self, params: dict, enabled: bool = True):
        # NOTE: params must be normalized already
        params = params.copy()
        for widget in self._mgui_widgets.values():
            if widget.name in params:
                new_value = params.pop(widget.name)
                if widget._nullable:
                    annotation = Union[widget.annotation, type(None)]
                else:
                    annotation = widget.annotation
                widget.value = parse_string(new_value, annotation)
            if not enabled:
                widget.enabled = False
        if params:
            _LOGGER.warning(
                f"Parameters not found in job directory: {list(params.keys())}"
            )

    def get_parameters(self) -> dict[str, Any]:
        """Get the parameters from the widgets."""
        params = {}
        for name, widget in self._mgui_widgets.items():
            params[name] = widget.value
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
        proc = job_cls.create_and_run_job(**params, _cwd=widget._cwd)
        widget.clear_content()
        if isinstance(proc, RelionJobExecution):
            widget._ui.read_file(proc.job_directory.path, append_history=False)
            widget._ui.show_notification(f"Job '{job_cls.job_title()}' started.")
        else:
            widget._ui.show_notification(f"Job '{job_cls.job_title()}' scheduled.")

    def button_text(self) -> str:
        return "Run Job"


class ContinueMode(Mode):
    def __init__(self, job_dir: _job_dir.JobDirectory):
        self.job_dir = job_dir

    def exec(self, widget: QJobScheduler):
        if not issubclass(job_cls := widget._current_job_cls, _Relion5BuiltinContinue):
            raise RuntimeError(f"Cannot continue this job type {job_cls!r}.")
        params = widget.get_parameters()
        proc = job_cls(self.job_dir).continue_job(**params)
        widget.clear_content()
        if isinstance(proc, RelionJobExecution):
            widget._ui.show_notification(f"Job '{job_cls.job_title()}' continued.")

    def button_text(self) -> str:
        return "Continue Job"


class EditMode(Mode):
    def __init__(self, job_dir: _job_dir.JobDirectory):
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
        widget._ui.show_notification(f"Job '{job_cls.job_title()}' Overwritten.")

    def button_text(self) -> str:
        return "Overwrite And Run"


class QParameterNameLabel(QtW.QWidget):
    def __init__(self, name: str, tooltip: str | None = None):
        super().__init__()
        self._tooltip = tooltip
        layout = QtW.QHBoxLayout(self)
        label = QtW.QLabel(f"<b>{name}</b>")
        layout.addWidget(label)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Minimum
        )

        if tooltip:
            svg = _utils.read_icon_svg("info")
            icon = QColoredSVGIcon(svg, color="gray")
            info_icon_widget = QParameterInfoIcon()
            info_icon_widget.setPixmap(icon.pixmap(12, 12))
            layout.addWidget(
                info_icon_widget, alignment=QtCore.Qt.AlignmentFlag.AlignRight
            )
            info_icon_widget.clicked.connect(self._on_info_icon_clicked)
        layout.setContentsMargins(0, 0, 0, 0)

    def _on_info_icon_clicked(self, pos: QtCore.QPoint):
        menu = QtW.QMenu(self)
        text_edit = QHTMLTextEdit(self._tooltip.replace("\n", "<br>"))
        action = QtW.QWidgetAction(menu)
        action.setDefaultWidget(text_edit)
        menu.addAction(action)
        adjusted_pos = QtCore.QPoint(pos.x() - 300, pos.y())
        menu.exec(adjusted_pos)


class QParameterInfoIcon(QtW.QLabel):
    """The (i) icon shown next to parameter names for displaying tooltips."""

    clicked = QtCore.Signal(QtCore.QPoint)

    def __init__(self):
        super().__init__()
        svg = _utils.read_icon_svg("info")
        icon = QColoredSVGIcon(svg, color="gray")
        self.setPixmap(icon.pixmap(12, 12))
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._last_press_pos = QtCore.QPoint()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self._last_press_pos = event.pos()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            dist = (event.pos() - self._last_press_pos).manhattanLength()
            if dist < 6:
                self.clicked.emit(event.globalPos())


class QHTMLTextEdit(QtW.QTextEdit):
    """A text edit used for displaying HTML content."""

    def __init__(self, html: str = ""):
        super().__init__()
        self.setReadOnly(True)
        self.setFixedSize(300, 150)
        self.setHtml(html)

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        self._anchor = self.anchorAt(e.pos())
        self.viewport().setCursor(
            QtCore.Qt.CursorShape.PointingHandCursor
            if self._anchor
            else QtCore.Qt.CursorShape.IBeamCursor
        )
        return super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(e)
        _anchor = self.anchorAt(e.pos())
        self.viewport().setCursor(
            QtCore.Qt.CursorShape.PointingHandCursor
            if _anchor
            else QtCore.Qt.CursorShape.IBeamCursor
        )
        if _anchor:
            self.setToolTip(f"Open in browser: {_anchor}")
        else:
            self.setToolTip("")
        return super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            _anchor = self.anchorAt(e.pos())
            if self._anchor == _anchor:
                QtGui.QDesktopServices.openUrl(QtCore.QUrl(self._anchor))
            self._anchor = None
        return super().mouseReleaseEvent(e)
