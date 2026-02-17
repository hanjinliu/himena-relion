# from __future__ import annotations

# from pathlib import Path

# from glob import glob
# from qtpy import QtCore, QtWidgets as QtW
# from watchfiles import watch
# from superqt.utils import thread_worker
# from himena_relion._widgets._job_widgets import QDirectoryTreeView, QFileSystemModel
# from himena_relion.schemas import JobStarModel

# class QTrashWidget(QtW.QSplitter):
#     """List of trashed jobs."""

#     list_changed = QtCore.Signal()

#     def __init__(self, project_dir: Path):
#         super().__init__(QtCore.Qt.Orientation.Horizontal)
#         self._project_dir = project_dir

#         self._job_list_widget = QtW.QListWidget()
#         self._content_tree_widget = QDirectoryTreeView()
#         self.addWidget(self._job_list_widget)
#         self.addWidget(self._content_tree_widget)

#         self._worker = self._watch_trash_dir()
#         self._update_job_list()

#         self._job_list_widget.itemSelectionChanged.connect(self._on_job_selected)

#     def trash_dir(self) -> Path:
#         return self._project_dir / "Trash"

#     @thread_worker(start_thread=True)
#     def _watch_trash_dir(self):
#         trash_dir = self.trash_dir()
#         if not trash_dir.exists():
#             return
#         for changes in watch(trash_dir, watch_filter=lambda path: Path(path).parent == trash_dir):
#             self._update_job_list()

#     def _update_job_list(self):
#         self._job_list_widget.clear()
#         trash_dir = self.trash_dir()
#         if not trash_dir.exists():
#             self._job_list_widget.clear()
#             model = QFileSystemModel(self)
#             self._content_tree_widget.setModel(model)
#             return
#         entries: list[tuple[str, str, Path]] = []
#         for job_path in glob(str(trash_dir / "*" / "job*")):
#             job_path = Path(job_path)
#             job_id = f"{job_path.parent.parent.name}/{job_path.parent.name}"
#             entries.append((job_path.parent.name, job_id, job_path))
#         entries.sort(key=lambda x: x[0])
#         for job_name, job_id, job_path in entries:
#             job_star = JobStarModel.validate_file(job_path / "job.star")
#             job_star.job.job_type_label
#             item = QtW.QListWidgetItem(job_name)
