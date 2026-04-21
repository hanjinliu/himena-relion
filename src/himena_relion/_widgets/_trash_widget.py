from __future__ import annotations

from pathlib import Path
import shutil
from glob import glob
from qtpy import QtCore, QtWidgets as QtW
from watchfiles import watch
from superqt.utils import thread_worker
from himena import WidgetDataModel
from himena.widgets import current_instance
from himena.plugins import register_widget_class, validate_protocol
from himena_relion._job_dir import JobDirectory
from himena_relion._widgets._main import QRelionJobWidgetBase
from himena_relion._widgets._job_widgets import QNoteEdit, QJobPipelineViewer
from himena_relion.consts import Type
from himena_relion.io._impl import restore_trashed_jobs, _html_list


class QTrashWidget(QtW.QSplitter):
    """Contents of the RELION Trash directory."""

    def __init__(self):
        super().__init__(QtCore.Qt.Orientation.Horizontal)
        self._project_dir = None
        self._watcher = None

        self._trash_label = QtW.QLabel("<b>Trashed jobs:</b>")
        font = self._trash_label.font()
        font.setPointSize(12)
        self._trash_label.setFont(font)
        self._job_list_widget = QtW.QListWidget()
        self._job_list_widget.setSelectionMode(
            QtW.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self._job_view = QRelionJobWidgetBase()
        self._job_view._state_widget._set_alias_btn.hide()

        left = QtW.QWidget()
        left_layout = QtW.QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._trash_label)
        left_layout.addWidget(self._job_list_widget)
        self.addWidget(left)
        self.addWidget(self._job_view)

        self._update_job_list()

        self._job_list_widget.itemSelectionChanged.connect(self._on_job_selected)
        self._job_list_widget.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._job_list_widget.customContextMenuRequested.connect(
            self._show_context_menu
        )
        self.setSizes([200, 640])

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        if not isinstance(model.value, Path):
            raise ValueError(f"Expected a Path, got {type(model.value)}")
        self._project_dir = model.value.parent
        self.widget_closed_callback()
        self._watcher = self._watch_trash_dir()
        self._update_job_list()

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self.trash_dir(),
            type=Type.RELION_TRASH,
        ).use_tab()

    def trash_dir(self) -> Path | None:
        if (
            self._project_dir is not None
            and (trash_dir := self._project_dir / "Trash").exists()
        ):
            return trash_dir

    @thread_worker(start_thread=True)
    def _watch_trash_dir(self):
        if trash_dir := self.trash_dir():
            for changes in watch(
                trash_dir,
                step=160,
                rust_timeout=400,
                yield_on_timeout=True,
            ):
                if self._watcher is None:
                    return  # stopped
                if changes:
                    self._update_job_list()
                yield

    @validate_protocol
    def widget_closed_callback(self):
        """Callback when the widget is closed."""
        if self._watcher is not None:
            self._watcher.quit()
            self._watcher = None

    def _update_job_list(self):
        self._job_list_widget.clear()
        trash_dir = self.trash_dir()
        if trash_dir is None:
            self._job_list_widget.clear()
            self._job_view.clear_tabs()
            return
        entries: list[str] = []
        for job_path in glob(str(trash_dir / "*" / "job*")):
            job_path = Path(job_path)
            job_id = f"{job_path.parent.name}/{job_path.name}/"
            entries.append(job_id)
        entries.sort(key=lambda x: x[0])
        for job_id in entries:
            item = QtW.QListWidgetItem(job_id)
            self._job_list_widget.addItem(item)

    def _on_job_selected(self):
        trash_dir = self.trash_dir()
        if trash_dir is None:
            return
        selected_items = self._job_list_widget.selectedItems()
        if not selected_items:
            self._job_view.clear_tabs()
            return
        job_id = selected_items[0].text()
        self._job_view.clear_tabs()
        self._job_view.update_job(
            JobDirectory.from_job_star(trash_dir / job_id / "job.star")
        )
        for widget in self._job_view._iter_job_widgets():
            if isinstance(widget, QNoteEdit):
                widget.setReadOnly(True)
            elif isinstance(widget, QJobPipelineViewer):
                widget._list_widget_in.setEnabled(False)
                widget._list_widget_out.setEnabled(False)

    def _make_context_menu(self):
        selected_items = self._job_list_widget.selectedItems()
        trash_dir = self.trash_dir()
        menu = QtW.QMenu(self)
        if trash_dir is None or not selected_items:
            return menu
        job_ids = [item.text() for item in selected_items]
        restore_action = menu.addAction(
            "Restore", lambda: restore_trashed_jobs(self._project_dir, job_ids)
        )
        restore_action.setToolTip("Restore the selected job(s).")
        rm_action = menu.addAction(
            "Delete Permanently", lambda: _delete_permanently(job_ids, trash_dir)
        )
        rm_action.setToolTip(
            "Delete the selected job(s) permanently. This action cannot be undone."
        )
        menu.addSeparator()
        copy_path_action = menu.addAction(
            "Copy Absolute Path(s)", lambda: _copy_job_paths(job_ids, trash_dir)
        )
        copy_path_action.setToolTip(
            "Copy the absolute paths of the selected job(s) to clipboard."
        )
        copy_rel_path_action = menu.addAction(
            "Copy Relative Path(s)", lambda: _copy_job_paths(job_ids, Path("Trash"))
        )
        copy_rel_path_action.setToolTip(
            "Copy the paths of the selected job(s) relative to the RELION project\n"
            "directory to clipboard."
        )
        return menu

    def _show_context_menu(self, pos):
        menu = self._make_context_menu()
        menu.exec(self._job_list_widget.viewport().mapToGlobal(pos))


def _copy_job_paths(job_ids: list[str], trash_dir: Path):
    paths = [str(trash_dir / job_id) for job_id in job_ids]
    QtW.QApplication.clipboard().setText("\n".join(paths))


def _delete_permanently(job_ids: list[str], trash_dir: Path):
    paths_to_del: list[Path] = []
    ids_to_del: list[str] = []
    for job_id in job_ids:
        job_path = trash_dir / job_id
        if job_path.exists() and job_path.is_dir():
            paths_to_del.append(job_path)
            ids_to_del.append(job_id)

    if current_instance().exec_choose_one_dialog(
        "Delete Permanently?",
        message=_html_list("Following jobs will be deleted permanently:", ids_to_del),
        choices=[("Yes, delete permanently", True), ("Cancel", False)],
    ):
        for job_path in paths_to_del:
            shutil.rmtree(job_path)


register_widget_class(Type.RELION_TRASH, QTrashWidget, priority=100)
