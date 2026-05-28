from __future__ import annotations
from collections import defaultdict
from contextlib import suppress
import datetime
from pathlib import Path

import logging
from typing import Annotated, Iterable
from qtpy import QtGui, QtWidgets as QtW, QtCore
from cmap import Color
from superqt import QElidingLabel
from superqt.utils import thread_worker, GeneratorWorker
from watchfiles import watch, Change

from himena import MainWindow, WidgetDataModel
from himena.plugins import validate_protocol
from himena.style import Theme
from himena.types import is_subtype
from himena.qt import QColoredToolButton
from himena.qt._qflowchart import TagItem, QFlowChartNode
from himena.exceptions import Cancelled
from himena.consts import MonospaceFontFamily
from himena.workflow import LocalReaderMethod
from himena_relion._job_class import execute_job
from himena_relion._job_dir import JobDirectory
from himena_relion._widgets import QRelionJobWidget
from himena_relion._widgets._job_widgets import QJobPipelineViewer
from himena_relion._widgets._misc import QMoreActionButton
from himena_relion._widgets._content_info import QJobContentInfo
from himena_relion.consts import Type, JOB_ID_MAP, FileNames
from himena_relion._pipeline import (
    NodeStatus,
    RelionDefaultPipeline,
    RelionJobInfo,
)
from himena_relion import _utils
from himena_relion.pipeline._gui_state import HimenaRelionGuiState
from himena_relion.pipeline._flowchart import (
    QRelionPipelineFlowChartView,
    RelionJobNodeItem,
)
from himena_relion.pipeline._table_view import QRelionPipelineTableView
from himena_relion.pipeline._startscreen import QRelionPipelineStartScreen
from himena_relion.io import _impl

_LOGGER = logging.getLogger(__name__)


class QRelionPipelineFlowChart(QtW.QWidget):
    """Widget to display RELION pipeline and manage job scheduling.

    You can switch between flowchart view and table view.
    Right click to show more actions.
    """

    update_required = QtCore.Signal(RelionDefaultPipeline)
    gui_state_reload_required = QtCore.Signal()

    def __init__(self, ui: MainWindow):
        super().__init__()
        self._relion_project_dir = Path.cwd()
        self._directory_label = QElidingLabel("???", self)
        self._directory_label.setFont(QtGui.QFont(MonospaceFontFamily, 10))
        self._directory_label.setElideMode(QtCore.Qt.TextElideMode.ElideLeft)
        self._directory_label.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Fixed
        )
        self._directory_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )

        # Create the "more" button with a menu for additional actions
        btn = QMoreActionButton(self)
        btn.setFixedHeight(18)
        btn.setToolTip("More actions ...")

        btn.add_action("Open default_pipeline.star", self._open_as_raw_text)
        btn.add_action("Open Project Note", self._open_project_note)
        btn.add_action("Open Trash", self._open_trash)
        btn.add_separator()
        btn.add_action("Find Job ...", self._find_job, shortcut="Ctrl+F")
        btn.add_action("New Job ...", self._new_job_palette, shortcut="Ctrl+Shift+J")
        # TODO: add these actions
        # btn.add_action("Gentle clean all", self._gentle_clean_all)
        # btn.add_action("Harsh clean all", self._harsh_clean_all)
        btn.add_action("Refresh", self._refresh_flowchart, shortcut="F5")
        btn.add_action("Copy Project Path", self._copy_project_path)
        btn.add_separator()
        btn.add_action("Open Running Jobs", self._open_all_running_jobs)
        btn.add_action("Open Last Completed Job", self._open_last_completed_job)
        btn.add_action("Close All Tabs", self._close_all_tabs)
        self._more_action_btn = btn

        self._stacked_widget = QtW.QStackedWidget()
        self._flow_chart = QRelionPipelineFlowChartView()
        self._table_view = QRelionPipelineTableView(self)
        self._start_screen = QRelionPipelineStartScreen(ui)
        self._stacked_widget.addWidget(self._flow_chart)
        self._stacked_widget.addWidget(self._table_view)
        self._stacked_widget.addWidget(self._start_screen)
        self._stacked_widget.setCurrentWidget(self._flow_chart)
        self._tool_buttons = [
            QColoredToolButton(self._new_job_palette, _utils.path_icon_svg("plus")),
            QColoredToolButton(self._find_job, _utils.path_icon_svg("find")),
            QColoredToolButton(self._switch_mode, _utils.path_icon_svg("switch_mode")),
        ]
        self._content_info = QJobContentInfo()
        self._inout = QJobPipelineViewer()

        self._footer = QtW.QWidget()
        _footer_layout = QtW.QVBoxLayout(self._footer)
        _footer_layout.setContentsMargins(0, 0, 0, 0)
        _hlayout = QtW.QHBoxLayout()
        _hlayout.setContentsMargins(0, 0, 0, 0)
        _hlayout.setSpacing(1)
        for tb in self._tool_buttons:
            tb.setFixedSize(16, 16)
            tb.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            _hlayout.addWidget(tb)
        _hlayout.addWidget(
            self._content_info, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        _footer_layout.addLayout(_hlayout)
        _footer_layout.addWidget(self._inout)

        self._watcher: GeneratorWorker | None = None
        self._gui_state_last_update_time = datetime.datetime.fromtimestamp(0)

        layout = QtW.QVBoxLayout(self)
        layout.setSpacing(0)
        splitter = QtW.QSplitter(QtCore.Qt.Orientation.Vertical)
        splitter.addWidget(self._stacked_widget)
        splitter.addWidget(self._footer)
        splitter.setSizes([800, 420])

        _header_layout = QtW.QHBoxLayout()
        _header_layout.setContentsMargins(0, 0, 0, 0)
        _header_layout.setSpacing(1)
        _header_layout.addWidget(self._directory_label)
        _header_layout.addWidget(btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addLayout(_header_layout)
        layout.addSpacing(2)
        layout.addWidget(splitter)

        # connect signals
        self._flow_chart.item_left_pressed.connect(self._on_item_left_pressed)
        self._flow_chart.item_right_pressed.connect(self._on_item_left_pressed)
        self._flow_chart.item_right_clicked.connect(self._on_right_clicked)
        self._flow_chart.item_left_double_clicked.connect(self._on_item_double_clicked)
        self._flow_chart.background_left_clicked.connect(
            self._on_background_left_clicked
        )
        self._flow_chart.background_right_clicked.connect(
            self._on_background_right_clicked
        )

        self._table_view.item_left_pressed.connect(self._on_item_left_pressed)
        self._table_view.item_right_pressed.connect(self._on_item_left_pressed)
        self._table_view.item_right_clicked.connect(self._on_right_clicked)
        self._table_view.item_left_double_clicked.connect(self._on_item_double_clicked)

        self._state_to_job_map = defaultdict[NodeStatus, dict[str, RelionJobInfo]](dict)
        self.update_required.connect(self._on_pipeline_updated)
        self.update_required.connect(self._on_job_state_changed)
        self.gui_state_reload_required.connect(self._on_gui_state_updated)

    def sizeHint(self):
        return QtCore.QSize(350, 600)

    def _on_item_left_pressed(self, item: RelionJobNodeItem):
        if job_dir := item.job_dir(self._relion_project_dir):
            self._inout.initialize(job_dir)
            self._inout.update_item_colors(job_dir)
            self._content_info.count_directory_content(job_dir.path)

    def _on_background_left_clicked(self):
        self._inout.clear_in_out()
        self._content_info.clear_content_info()

    def _on_item_double_clicked(self, item: RelionJobNodeItem):
        path = self._relion_project_dir / item.id()
        if path.exists():
            _utils.read_or_show_job(self._ui(), path)
        else:
            raise FileNotFoundError(f"File {path} does not exist.")

    def _ui(self):
        return self._start_screen._ui

    def _pipeline(self) -> RelionDefaultPipeline:
        return self._flow_chart._pipeline

    def _open_as_raw_text(self):
        """Open the default_pipeline.star file as a raw text file."""
        path = self._relion_project_dir / "default_pipeline.star"
        if not path.exists():
            _LOGGER.warning("default_pipeline.star not found at %s.", path.as_posix())
            return
        self._ui().read_file(
            path,
            plugin="himena_builtins.io.read_as_text_anyway",
            append_history=False,
        )

    def _open_project_note(self):
        """Open and edit the project note file."""
        path = self._relion_project_dir / "project_note.txt"
        if not path.exists():
            path.touch()  # create an empty project_note.txt if it doesn't exist
        self._ui().read_file(path, append_history=False)

    def _refresh_flowchart(self):
        """Manually trigger a refresh of the pipeline data."""
        self._on_pipeline_updated(self._pipeline())

    def _copy_project_path(self):
        """Copy the RELION project path to clipboard."""
        path = self._relion_project_dir.as_posix()
        self._ui().set_clipboard(text=path)
        self._ui().show_notification(f"Copied project path {path!r} to clipboard.")

    def _close_all_tabs(self):
        """Close all tabs in the main window that contain jobs from this pipeline."""
        indices: list[int] = []
        for i_tab, tab in self._ui().tabs.enumerate():
            if not tab.is_single_window:
                continue
            if is_subtype(tab[0].model_type(), Type.RELION_JOB):
                indices.append(i_tab)
        for i in reversed(indices):
            del self._ui().tabs[i]

    @validate_protocol
    def update_model(self, model: WidgetDataModel) -> None:
        if not isinstance(src := model.source, Path):
            raise TypeError("RELION default_pipeline.star source file not found.")
        assert isinstance(model.value, RelionDefaultPipeline)
        _LOGGER.info("Started watching RELION pipeline at %s.", src.parent.as_posix())
        self._relion_project_dir = src.parent
        self._init_watcher()
        self._on_pipeline_updated(model.value)
        parts = src.parts
        if len(parts) >= 3:
            self._directory_label.setText(f"{parts[-3]}/{parts[-2]}/")
        else:
            self._directory_label.setText(f"{parts[-2]}/")
        self._watcher = self._watch_default_pipeline_star(src)
        self._state_to_job_map.clear()
        for job in model.value.iter_nodes():
            _dict = self._state_to_job_map[job.status]
            _dict[job.path.as_posix() + "/"] = job

    def _on_pipeline_updated(self, pipeline: RelionDefaultPipeline) -> None:
        self._flow_chart.set_pipeline(pipeline)
        self._table_view.set_pipeline(pipeline)
        self._flow_chart.read_gui_state(pipeline)
        self._table_view.read_gui_state(pipeline)
        cur_widget = self._stacked_widget.currentWidget()
        if len(pipeline) == 0:
            self._stacked_widget.setCurrentWidget(self._start_screen)
        elif cur_widget == self._start_screen:
            self._stacked_widget.setCurrentWidget(self._flow_chart)

    def _on_gui_state_updated(self) -> None:
        self._flow_chart.read_gui_state(self._pipeline())
        self._table_view.read_gui_state(self._pipeline())

    @validate_protocol
    def model_type(self) -> str:
        return Type.RELION_PIPELINE

    @validate_protocol
    def size_hint(self):
        hint = self.sizeHint()
        return (hint.width(), hint.height())

    @validate_protocol
    def theme_changed_callback(self, theme: Theme) -> None:
        self._flow_chart.setBackgroundBrush(QtGui.QColor(Color(theme.background).hex))
        for btn in self._tool_buttons:
            btn.update_color(theme.foreground)
        self._table_view._sort_ascending_btn.update_color(theme.foreground)

    def _init_watcher(self):
        if self._watcher:
            self._watcher.quit()
            self._watcher = None

    @validate_protocol
    def widget_closed_callback(self) -> None:
        self._init_watcher()

    def closeEvent(self, a0):
        self.widget_closed_callback()
        return super().closeEvent(a0)

    @thread_worker(start_thread=True)
    def _watch_default_pipeline_star(self, path: Path):
        """Watch the job directory for changes."""
        for changes in watch(path, rust_timeout=400, yield_on_timeout=True):
            if self._watcher is None:
                _LOGGER.info("Pipeline watcher stopped.")
                return  # stopped
            for change, fp in changes:
                if change == Change.deleted:
                    continue
                _LOGGER.info("default_pipeline.star updated.")
                try:
                    pipeline = RelionDefaultPipeline.from_pipeline_star(path)
                except Exception:
                    _LOGGER.warning(
                        "Failed to read default_pipeline.star", exc_info=True
                    )
                else:
                    # Update the internal data (thus, the flow chart)
                    self.update_required.emit(pipeline)
            yield
            # read GUI state if updated
            if state := HimenaRelionGuiState.try_from_project_directory(path.parent):
                written_time = state._write_time
                if self._gui_state_last_update_time < written_time:
                    self._gui_state_last_update_time = written_time
                    self.gui_state_reload_required.emit()
                    yield

    def _on_job_state_changed(self, pipeline: RelionDefaultPipeline):
        success_old = set(self._state_to_job_map[NodeStatus.SUCCEEDED].keys())
        failed_old = set(self._state_to_job_map[NodeStatus.FAILED].keys())
        aborted_old = set(self._state_to_job_map[NodeStatus.ABORTED].keys())
        running_old = set(self._state_to_job_map[NodeStatus.RUNNING].keys())
        scheduled_old = set(self._state_to_job_map[NodeStatus.SCHEDULED].keys())
        self._state_to_job_map.clear()
        for job in pipeline.iter_nodes():
            _dict = self._state_to_job_map[job.status]
            _dict[job.path.as_posix()] = job
        success_new = set(self._state_to_job_map[NodeStatus.SUCCEEDED].keys())
        failed_new = set(self._state_to_job_map[NodeStatus.FAILED].keys())
        running_new = set(self._state_to_job_map[NodeStatus.RUNNING].keys())
        scheduled_new = set(self._state_to_job_map[NodeStatus.SCHEDULED].keys())
        ui = self._ui()

        to_notify: list[str] = []
        # Notify newly succeeded jobs and run scheduled jobs
        if succeeded := (success_new - success_old) & running_old:
            to_notify.append("\n".join(f"Job {job} succeeded." for job in succeeded))

        # Notify newly failed jobs
        if failed := (failed_new - failed_old) & running_old:
            to_notify.append("\n".join(f"Job {job} failed." for job in failed))

        _finished = success_old | failed_old | aborted_old
        # Notify newly scheduled jobs
        if scheduled := (scheduled_new - scheduled_old) & _finished:
            to_notify.append("\n".join(f"Job {job} scheduled." for job in scheduled))

        # Notify newly running jobs
        if started := (running_new - running_old) & (_finished | scheduled_old):
            to_notify.append("\n".join(f"Job {job} started." for job in started))

            # if job is opened, force update (because this may not trigger any file
            # change)
            for window in self._ui().iter_windows():
                if (
                    isinstance(widget := window.widget, QRelionJobWidget)
                    and widget._job_dir.job_normal_id() in started
                ):
                    widget._state_widget.initialize(widget._job_dir)

        if to_notify:
            ui.show_notification("\n".join(to_notify), title="Pipeline Updates")

    def keyPressEvent(self, a0):
        key = a0.key()
        mod = a0.modifiers()
        if key == QtCore.Qt.Key.Key_Return:
            for item in self._iter_selected_items():
                self._on_item_double_clicked(item)
                return
        elif (
            key == QtCore.Qt.Key.Key_F
            and mod & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self._find_job()
            return
        elif (
            key == QtCore.Qt.Key.Key_J
            and mod & QtCore.Qt.KeyboardModifier.ControlModifier
            and mod & QtCore.Qt.KeyboardModifier.ShiftModifier
        ):
            self._new_job_palette()
            return
        elif key == QtCore.Qt.Key.Key_F5:
            self._refresh_flowchart()
            return
        elif key == QtCore.Qt.Key.Key_Delete:
            for item in self._iter_selected_items():
                self._trash_job(item)
            return
        return super().keyPressEvent(a0)

    def _iter_selected_items(self) -> Iterable[RelionJobNodeItem]:
        if self._stacked_widget.currentWidget() == self._flow_chart:
            for qitem in self._flow_chart.scene().selectedItems():
                if isinstance(qitem, QFlowChartNode) and isinstance(
                    item := qitem.item(), RelionJobNodeItem
                ):
                    yield item
        elif self._stacked_widget.currentWidget() == self._table_view:
            if item := self._table_view.current_item():
                yield item

    def _find_job(self):
        """Find a job in the flowchart by its name, ID or state."""
        choices = _list_jobs_for_palette(
            self._pipeline(),
            self._node_id_to_tags_map(),
        )
        if resp := self._ui().exec_choose_one_dialog(
            title="Select the root job.",
            message="Search by name, @state, #tag",
            choices=choices,
            how="palette",
        ):
            self._center_on_item(resp.path)

    def _center_on_item(self, path: Path):
        if self._stacked_widget.currentWidget() is self._flow_chart:
            if node := self._flow_chart._node_map.get(path):
                self._flow_chart.center_on_item(node.item())
        elif self._stacked_widget.currentWidget() is self._table_view:
            self._table_view.center_on_item(path)

    def _switch_mode(self):
        """Switch between flowchart view and table view."""
        if self._stacked_widget.currentWidget() == self._start_screen:
            pass
        elif self._stacked_widget.currentWidget() == self._flow_chart:
            self._stacked_widget.setCurrentWidget(self._table_view)
            if item := self._flow_chart.current_item():
                self._table_view.center_on_item(item.id())
            self._table_view.read_gui_state(self._pipeline())
        else:
            self._stacked_widget.setCurrentWidget(self._flow_chart)
            self._flow_chart.read_gui_state(self._pipeline())
            if item := self._table_view.current_item():
                self._flow_chart.center_on_item(item)

    def _on_background_right_clicked(self):
        btn = self._more_action_btn
        btn.menu().exec(QtGui.QCursor.pos())

    def _open_trash(self):
        """Open a widget that shows the contents of the RELION Trash directory."""
        self._ui().read_file(self._relion_project_dir / "Trash", append_history=False)

    def _trash_job(self, item: RelionJobNodeItem):
        """Move a job to the RELION Trash directory."""
        from himena_relion.io import _impl

        if job_dir := item.job_dir(self._relion_project_dir):
            _impl.trash_job(self._ui(), job_dir)

    def _new_job_palette(self):
        """Create a new RELION job."""
        from himena_relion.io import _impl

        _impl.new_job(self._ui(), ignore_cancelled=True)

    def _open_all_running_jobs(self):
        """Open all the running jobs in this pipeline."""
        running_jobs = list(self._state_to_job_map[NodeStatus.RUNNING].values())
        if len(running_jobs) > 0:
            for job in self._state_to_job_map[NodeStatus.RUNNING].values():
                _utils.read_or_show_job(self._ui(), job.path)
        else:
            self._ui().show_notification("No running jobs to open.")

    def _open_last_completed_job(self):
        """Open the last completed job in this pipeline."""
        succeeded_jobs = list(self._state_to_job_map[NodeStatus.SUCCEEDED].values())
        if len(succeeded_jobs) > 0:
            last_job = max(succeeded_jobs, key=lambda job: _exit_success_time(job))
            self._center_on_item(last_job.path)
            if (path := self._relion_project_dir / last_job.path).exists():
                return _utils.read_or_show_job(self._ui(), path)
        self._ui().show_notification("No completed jobs to open.")

    def _node_id_to_tags_map(self) -> dict[str, list[str]]:
        id_to_tags_map = {}
        chart = self._flow_chart
        for node_id in chart._node_map.keys():
            id_to_tags_map[node_id] = [
                t.name.replace(" ", "_") for t in chart.item_tags(node_id)
            ]
        return id_to_tags_map

    def _on_right_clicked(self, item: RelionJobNodeItem):
        menu = self._prep_right_click_menu(item)
        menu.exec(QtGui.QCursor.pos())

    def _prep_right_click_menu(self, item: RelionJobNodeItem):
        self._flow_chart.read_gui_state(self._pipeline())
        self._table_view.read_gui_state(self._pipeline())
        path = self._relion_project_dir / item.id() / "job.star"
        ui = self._ui()

        def get_job():
            return JobDirectory.from_job_star(path)

        status = item._job.status
        menu = QtW.QMenu(self)
        menu.setToolTipsVisible(True)
        submenu_file = menu.addMenu("File")
        submenu_job = menu.addMenu("Job")
        submenu_tag = menu.addMenu("Tag")
        submenu_file.addAction(
            "Open 'job.star' As Text",
            lambda: _impl.open_relion_job_star(ui, get_job()),
        )
        submenu_file.addAction(
            "Open 'job_pipeline.star' As Text",
            lambda: _impl.open_relion_job_pipeline_star(ui, get_job()),
        )
        submenu_file.addAction(
            "Open Job Parameters",
            lambda: _impl.open_job_parameters(ui, get_job()),
        )
        submenu_file.addSeparator()
        submenu_file.addAction(
            "Copy Directory Path",
            lambda: ui.set_clipboard(text=str(path.parent)),
        )
        submenu_file.addAction(
            "Copy Directory Relative Path",
            lambda: ui.set_clipboard(text=str(item.id())),
        )
        action = submenu_job.addAction(
            "Gentle Clean", lambda: _impl.gentle_clean_relion_job(ui, get_job())
        )
        action.setEnabled(status is NodeStatus.SUCCEEDED)
        action = submenu_job.addAction(
            "Harsh Clean", lambda: _impl.harsh_clean_relion_job(ui, get_job())
        )
        submenu_job.addSeparator()
        action.setEnabled(status is NodeStatus.SUCCEEDED)
        action = submenu_job.addAction(
            "Mark As Finished", lambda: _impl.mark_as_finished(get_job())
        )
        action.setEnabled(status is not NodeStatus.SUCCEEDED)
        action = submenu_job.addAction(
            "Mark As Failed", lambda: _impl.mark_as_failed(get_job())
        )
        action.setEnabled(status is not NodeStatus.FAILED)
        self._prep_tag_menu(submenu_tag, item)

        menu.addSeparator()

        # Prepare next actions
        action_hints = _create_action_hint_menu(ui, path)
        if action_hints:
            action_hint_menu = menu.addMenu("Next Action ...")
            for action in action_hints:
                action.setParent(action_hint_menu)
                action_hint_menu.addAction(action)

        # Abort
        action = menu.addAction(
            "Abort", lambda: _ignore_cancel(_impl.abort_relion_job, ui, get_job())
        )
        action.setEnabled(status is NodeStatus.RUNNING)
        action.setToolTip("Notify the job to be aborted.")
        # Run now
        action = menu.addAction(
            "Run This Scheduled Job Now",
            lambda: execute_job(item.id(), cwd=self._relion_project_dir),
        )
        action.setToolTip(
            "Run this scheduled job immediately, regardless of whether all the parent\n"
            "jobs have finished or not."
        )
        action.setEnabled(status is NodeStatus.SCHEDULED)
        # Overwrite
        action = menu.addAction(
            "Overwrite ...", lambda: _impl.overwrite_relion_job(ui, get_job())
        )
        action.setToolTip(
            "Overwrite this job by re-running it with a new set of parameters."
        )
        # Clone
        action = menu.addAction(
            "Clone ...", lambda: _impl.clone_relion_job(ui, get_job())
        )
        action.setToolTip("Create a same type of job with a new set of parameters.")

        menu.addAction(
            "Set Alias ...",
            lambda: _ignore_cancel(_impl.set_job_alias, ui, get_job()),
        )
        action = menu.addAction(
            "Trash This Job", lambda: _ignore_cancel(_impl.trash_job, ui, get_job())
        )
        action.setToolTip(
            "Move this job to the Trash directory under this project (will pop up a\n"
            "confirmation dialog)."
        )
        action.setEnabled(status is not NodeStatus.RUNNING)
        menu.addSeparator()

        # parent/child jobs
        parent_menu = menu.addMenu("Parent Jobs")
        child_menu = menu.addMenu("Child Jobs")

        existing_ids = set()
        for parent in item._job.parents:
            if (
                job_id := _utils.normalize_job_id(parent.node.path)
            ) not in existing_ids:
                action = parent_menu.addAction(
                    job_id,
                    lambda p=parent.node.path: self._center_on_item(p),
                )
                existing_ids.add(job_id)
        if len(item._job.parents) == 0:
            parent_menu.setEnabled(False)

        existing_ids = set()
        for child in item._job.children:
            if (job_id := _utils.normalize_job_id(child.node.path)) not in existing_ids:
                action = child_menu.addAction(
                    job_id,
                    lambda c=child.node.path: self._center_on_item(c),
                )
                existing_ids.add(job_id)
        if len(item._job.children) == 0:
            child_menu.setEnabled(False)

        return menu

    def _prep_tag_menu(self, tag_menu: QtW.QMenu, item: RelionJobNodeItem):
        fc = self._flow_chart
        current_item_tags = fc.item_tags(item.id())
        current_all_tags = fc.tags()
        actions = []

        def _set_tag():
            tags: list[TagItem] = []
            for ac, tag in zip(actions, current_all_tags, strict=True):
                if ac.isChecked():
                    tags.append(tag)
            fc.set_item_tags(item.id(), tags)
            fc.save_gui_state(self._pipeline())

        for tag in current_all_tags:
            action = tag_menu.addAction(tag.name, _set_tag)
            action.setCheckable(True)  # This is needed for _set_tag()
            checked = tag in current_item_tags
            action.setChecked(checked)
            action.setIcon(_make_tag_icon(tag.color, checked=checked))
            actions.append(action)

        tag_menu.addSeparator()
        action = tag_menu.addAction("Manage Tags ...", self._manage_tags)
        action.setToolTip("Edit tag names")

    def _manage_tags(self):
        current_all_tags = self._flow_chart.tags()
        sig = {}
        for ith, tag in enumerate(current_all_tags):
            sig[f"x{ith}"] = Annotated[
                str, {"label": f"({ith + 1})", "value": tag.name}
            ]
        if out := self._ui().exec_user_input_dialog(sig, title="Manage Tags"):
            for ith, tag_name in enumerate(out.values()):
                self._flow_chart.edit_tag(ith, tag_name, tooltip=tag_name)
            self._flow_chart.save_gui_state(self._pipeline())


def _make_tag_icon(color: Color, checked: bool = False) -> QtGui.QIcon:
    pixmap = QtGui.QPixmap(32, 32)
    bg = QtGui.QColor.fromRgbF(*color.rgba)
    pixmap.fill(bg)
    if checked:
        painter = QtGui.QPainter(pixmap)
        if bg.lightnessF() < 0.5:
            pen_color = QtGui.QColor("white")
        else:
            pen_color = QtGui.QColor("black")
        pen = QtGui.QPen(pen_color, 4)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPolyline(
            [QtCore.QPoint(7, 17), QtCore.QPoint(13, 23), QtCore.QPoint(25, 11)]
        )
        painter.end()
    return QtGui.QIcon(pixmap)


def _exit_success_time(job: RelionJobInfo) -> float:
    try:
        return job.path.joinpath(FileNames.EXIT_SUCCESS).stat().st_mtime
    except FileNotFoundError:
        return 0.0


def _list_jobs_for_palette(
    pipeline: RelionDefaultPipeline,
    id_to_tags_map: dict[str, list[str]] = {},
) -> list[tuple[str, RelionJobInfo]]:
    out = []
    for info in pipeline.iter_nodes():
        jobxxx = info.path.stem
        if jobxxx.startswith("job"):
            jobxxx = jobxxx[3:]
        state = info.status.value.title()
        title = JOB_ID_MAP.get(info.type_label, info.type_label)
        if info.alias:
            title = f"{info.alias} ({title})"
        tags_str = " ".join(f"#{tag}" for tag in id_to_tags_map.get(info.path, []))
        display_text = f"{jobxxx}: {title} @{state} {tags_str}"
        out.append((display_text, info))
    return out


def _create_action_hint_menu(ui: MainWindow, job_star_path: Path) -> list[QtW.QAction]:
    actions = []
    try:
        model_type = JobDirectory.from_job_star(job_star_path).himena_model_type()
        method = LocalReaderMethod(
            path=job_star_path,
            plugin="himena_relion.io.read_relion_job",
            output_model_type=model_type,
        )
        for attr, exe in ui.action_hint_registry.iter_executors(ui, model_type, method):
            action = QtW.QAction(attr.title)
            action.triggered.connect(exe)
            action.setToolTip(attr.tooltip)
            actions.append(action)
    except Exception as e:
        ui.show_notification(f"Failed to create action hint menu: {e}", title="Warning")
    return actions


def _ignore_cancel(func, *args, **kwargs):
    """Decorator to ignore Cancelled exception."""
    with suppress(Cancelled):
        return func(*args, **kwargs)
