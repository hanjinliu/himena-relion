from __future__ import annotations
from collections import defaultdict
from pathlib import Path

import logging
from qtpy import QtGui, QtWidgets as QtW, QtCore
from cmap import Color
from superqt import QSearchableComboBox, QElidingLabel
from superqt.utils import thread_worker, GeneratorWorker
from watchfiles import watch, Change

from himena import MainWindow, WidgetDataModel
from himena.plugins import validate_protocol
from himena.style import Theme
from himena.types import is_subtype
from himena_relion._job_class import execute_job
from himena_relion._widgets._job_widgets import QJobPipelineViewer
from himena_relion._widgets._misc import QMoreActionButton
from himena_relion.consts import Type, JOB_ID_MAP
from himena_relion._pipeline import (
    NodeStatus,
    RelionDefaultPipeline,
    RelionJobInfo,
    is_all_inputs_ready,
)
from himena_relion.pipeline._flowchart import (
    QRelionPipelineFlowChartView,
    RelionJobNodeItem,
)
from himena_relion._widgets._content_info import QJobContentInfo
from himena_relion.pipeline._startscreen import QRelionPipelineStartScreen

_LOGGER = logging.getLogger(__name__)


class QRelionPipelineFlowChart(QtW.QWidget):
    """Widget to display RELION pipeline flow chart and manage scheduling.

    Right click to show more actions.
    """

    update_required = QtCore.Signal(RelionDefaultPipeline)

    def __init__(self, ui: MainWindow):
        super().__init__()
        self._directory_label = QElidingLabel("???", self)
        self._directory_label.setElideMode(QtCore.Qt.TextElideMode.ElideLeft)
        self._directory_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._scene = QtW.QGraphicsScene()

        # Create the "more" button with a menu for additional actions
        btn = QMoreActionButton(self)
        btn.setFixedHeight(18)
        btn.setToolTip("More actions ...")

        btn.add_action("Open default_pipeline.star", self._open_as_raw_text)
        btn.add_action("Open Project Note", self._open_project_note)
        btn.add_action("Open Trash", self._open_trash)
        btn.add_separator()
        btn.add_action("Find Job ...", self._find_job, shortcut="Ctrl+F")
        btn.add_action("Set Root Job ...", self._set_root_job)
        btn.add_action("Unset Root Job", self._unset_root_job)
        # TODO: add these actions
        # btn.add_action("Gentle clean all", self._gentle_clean_all)
        # btn.add_action("Harsh clean all", self._harsh_clean_all)
        btn.add_action("Refresh", self._refresh_flowchart, shortcut="F5")
        btn.add_action("Copy Project Path", self._copy_project_path)
        btn.add_action("Close All Tabs", self._close_all_tabs)
        self._more_action_btn = btn

        self._stacked_widget = QtW.QStackedWidget()
        self._flow_chart = QRelionPipelineFlowChartView(ui, self._scene)
        self._start_screen = QRelionPipelineStartScreen(ui)
        self._stacked_widget.addWidget(self._flow_chart)
        self._stacked_widget.addWidget(self._start_screen)
        self._stacked_widget.setCurrentWidget(self._flow_chart)
        self._content_info = QJobContentInfo()
        self._inout = QJobPipelineViewer()

        self._footer = QtW.QWidget()
        _footer_layout = QtW.QVBoxLayout(self._footer)
        _footer_layout.setContentsMargins(0, 0, 0, 0)
        _footer_layout.addWidget(self._content_info)
        _footer_layout.addWidget(self._inout)

        self._watcher: GeneratorWorker | None = None
        layout = QtW.QVBoxLayout(self)
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
        layout.addWidget(splitter)

        self._flow_chart.item_left_clicked.connect(self._on_item_left_clicked)
        self._flow_chart.item_right_clicked.connect(self._on_item_left_clicked)
        self._flow_chart.background_left_clicked.connect(
            self._on_background_left_clicked
        )
        self._flow_chart.background_right_clicked.connect(
            self._on_background_right_clicked
        )

        self._state_to_job_map = defaultdict[NodeStatus, dict[str, RelionJobInfo]](dict)
        self.update_required.connect(self._on_pipeline_updated)
        self.update_required.connect(self._on_job_state_changed)

    def sizeHint(self):
        return QtCore.QSize(350, 600)

    def _on_item_left_clicked(self, item: RelionJobNodeItem):
        if job_dir := item.job_dir(self._flow_chart._relion_project_dir):
            self._inout.initialize(job_dir)
            self._inout.update_item_colors(job_dir)
            self._content_info.count_directory_content(job_dir.path)
        else:
            self._on_background_left_clicked()

    def _on_background_left_clicked(self):
        self._inout.clear_in_out()
        self._content_info.clear_content_info()

    def _ui(self):
        return self._flow_chart._ui

    def _open_as_raw_text(self):
        """Open the default_pipeline.star file as a raw text file."""
        path = self._flow_chart._relion_project_dir / "default_pipeline.star"
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
        path = self._flow_chart._relion_project_dir / "project_note.txt"
        if not path.exists():
            path.touch()  # create an empty project_note.txt if it doesn't exist
        self._ui().read_file(path, append_history=False)

    def _set_root_job(self):
        """Set a job as the root of the flowchart.

        Only the descendants jobs of the root job will be shown in the flowchart. This
        operation is just a filtering and does not modify the underlying pipeline star
        file.
        """
        choices = _list_jobs_for_palette(self._flow_chart._pipeline)
        if resp := self._ui().exec_choose_one_dialog(
            message="Select the root job.",
            choices=choices,
            how="palette",
        ):
            self._flow_chart.set_root_job(resp)

    def _unset_root_job(self):
        """Restore the full flowchart by clearing the root job."""
        self._flow_chart.set_root_job(None)

    def _refresh_flowchart(self):
        """Manually trigger a refresh of the pipeline data."""
        self._on_pipeline_updated(self._flow_chart._pipeline)

    def _copy_project_path(self):
        """Copy the RELION project path to clipboard."""
        path = self._flow_chart._relion_project_dir.as_posix()
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
        self._flow_chart._relion_project_dir = src.parent
        self.widget_closed_callback()
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
            _dict[job.path.as_posix()] = job

    def _on_pipeline_updated(self, pipeline: RelionDefaultPipeline) -> None:
        self._flow_chart.set_pipeline(pipeline)
        if len(pipeline) == 0:
            self._stacked_widget.setCurrentWidget(self._start_screen)
        else:
            self._stacked_widget.setCurrentWidget(self._flow_chart)

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

    @validate_protocol
    def widget_closed_callback(self) -> None:
        if self._watcher:
            self._watcher.quit()
            self._watcher = None

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

    def _on_job_state_changed(self, pipeline: RelionDefaultPipeline) -> None:
        success_old = set(self._state_to_job_map[NodeStatus.SUCCEEDED].keys())
        failed_old = set(self._state_to_job_map[NodeStatus.FAILED].keys())
        running_old = set(self._state_to_job_map[NodeStatus.RUNNING].keys())
        self._state_to_job_map.clear()
        for job in pipeline.iter_nodes():
            _dict = self._state_to_job_map[job.status]
            _dict[job.path.as_posix()] = job
        success_new = set(self._state_to_job_map[NodeStatus.SUCCEEDED].keys())
        failed_new = set(self._state_to_job_map[NodeStatus.FAILED].keys())
        ui = self._ui()
        # Notify newly succeeded jobs and run scheduled jobs
        if succeeded := (success_new - success_old) & running_old:
            for job in self._state_to_job_map[NodeStatus.SCHEDULED].values():
                # run all the scheduled jobs whose dependencies are met
                if is_all_inputs_ready(job.path):
                    execute_job(
                        job.path.as_posix(),
                        cwd=pipeline._project_dir,
                    )
                    ui.show_notification(f"Scheduled job {job.job_repr()} started.")
            ui.show_notification(
                "\n".join(f"Job {job}/ succeeded." for job in succeeded)
            )

        # Notify newly failed jobs
        if failed := failed_new - failed_old:
            ui.show_notification("\n".join(f"Job {job}/ failed." for job in failed))

    def keyPressEvent(self, a0):
        key = a0.key()
        mod = a0.modifiers()
        if key == QtCore.Qt.Key.Key_Return:
            for item in self._flow_chart.scene().selectedItems():
                if isinstance(item, RelionJobNodeItem):
                    self._flow_chart._on_item_double_clicked(item)
                    return
        elif (
            key == QtCore.Qt.Key.Key_F
            and mod & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self._find_job()
            return
        elif key == QtCore.Qt.Key.Key_F5:
            self._refresh_flowchart()
            return
        elif key == QtCore.Qt.Key.Key_Delete:
            for item in self._flow_chart.scene().selectedItems():
                if isinstance(item, RelionJobNodeItem):
                    self._trash_job(item)
            return
        return super().keyPressEvent(a0)

    def _find_job(self):
        """Find a job in the flowchart and center on it."""
        choices = _list_jobs_for_palette(self._flow_chart._pipeline)
        if resp := self._ui().exec_choose_one_dialog(
            message="Select the root job.",
            choices=choices,
            how="palette",
        ):
            if node := self._flow_chart._node_map.get(resp.path):
                self._flow_chart.center_on_item(node.item())

    def _on_background_right_clicked(self):
        btn = self._more_action_btn
        btn.menu().exec(QtGui.QCursor.pos())

    def _open_trash(self):
        """Open a widget that shows the contents of the RELION Trash directory."""
        self._ui().read_file(
            self._flow_chart._relion_project_dir / "Trash", append_history=False
        )

    def _trash_job(self, item: RelionJobNodeItem):
        """Move a job to the RELION Trash directory."""
        from himena_relion.io import _impl

        if job_dir := item.job_dir(self._flow_chart._relion_project_dir):
            _impl.trash_job(self._ui(), job_dir)


class QPipelineFinder(QSearchableComboBox):
    def set_selected(self):
        return self.lineEdit().selectAll()


def _list_jobs_for_palette(
    pipeline: RelionDefaultPipeline,
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
        display_text = f"{jobxxx}: {title} [{state}]"
        out.append((display_text, info))
    return out
