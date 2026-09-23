"""A lazy file system model for directories that QFileSystemModel cannot show.

QFileSystemModel checks the existence of the host of a UNC path (such as
`\\\\wsl.localhost`), which always fails for WSL paths. This model lists directories
with `os.scandir` only when they are expanded.
"""

from __future__ import annotations

from bisect import bisect_left
from datetime import datetime
import os
from pathlib import Path
from qtpy import QtWidgets as QtW, QtCore

_ItemDataRole = QtCore.Qt.ItemDataRole


def path_tooltip(path: Path) -> str:
    """Tooltip text showing the size and the last modified time of the path."""
    try:
        stat = path.stat()
    except OSError:
        return "<Deleted>"
    size_human_readable = QtCore.QLocale().formattedDataSize(stat.st_size, 2)
    time_last_modified = datetime.fromtimestamp(stat.st_mtime)
    return (
        f"{path.as_posix()}\n"
        f"Size: {size_human_readable}\n"
        f"Last modified: {time_last_modified:%Y-%m-%d %H:%M:%S}"
    )


class _Node:
    def __init__(self, path: Path, is_dir: bool, parent: _Node | None = None):
        self.path = path
        self.is_dir = is_dir
        self.parent = parent
        self.children: list[_Node] | None = None  # None if not scanned yet

    @property
    def sort_key(self) -> tuple[bool, str]:
        return (not self.is_dir, self.path.name.lower())

    def row(self) -> int:
        if self.parent is None or self.parent.children is None:
            return 0
        return self.parent.children.index(self)

    def scan(self) -> list[_Node]:
        """List the directory content, sorted in the same way as the file explorer."""
        nodes = []
        try:
            with os.scandir(self.path) as it:
                for entry in it:
                    try:
                        is_dir = entry.is_dir()
                    except OSError:
                        is_dir = False
                    nodes.append(_Node(Path(entry.path), is_dir, self))
        except OSError:
            pass
        nodes.sort(key=lambda n: n.sort_key)
        return nodes


class QScandirModel(QtCore.QAbstractItemModel):
    """A single-column, lazily populated file system model rooted at `root`."""

    def __init__(self, root: Path | str, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self._root = _Node(Path(root), is_dir=True)
        self._root.children = self._root.scan()
        provider = QtW.QFileIconProvider()
        self._dir_icon = provider.icon(QtW.QFileIconProvider.IconType.Folder)
        self._file_icon = provider.icon(QtW.QFileIconProvider.IconType.File)

    def rootPath(self) -> str:
        return str(self._root.path)

    def filePath(self, index: QtCore.QModelIndex) -> str:
        return str(self._node(index).path)

    def _node(self, index: QtCore.QModelIndex) -> _Node:
        if index.isValid():
            return index.internalPointer()
        return self._root

    def index(self, row, column=0, parent=QtCore.QModelIndex()) -> QtCore.QModelIndex:
        children = self._node(parent).children
        if column != 0 or children is None or not 0 <= row < len(children):
            return QtCore.QModelIndex()
        return self.createIndex(row, column, children[row])

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()
        parent = index.internalPointer().parent
        if parent is None or parent is self._root:
            return QtCore.QModelIndex()
        return self.createIndex(parent.row(), 0, parent)

    def rowCount(self, parent=QtCore.QModelIndex()) -> int:
        if parent.column() > 0:
            return 0
        children = self._node(parent).children
        return 0 if children is None else len(children)

    def columnCount(self, parent=QtCore.QModelIndex()) -> int:
        return 1

    def hasChildren(self, parent=QtCore.QModelIndex()) -> bool:
        node = self._node(parent)
        if node.children is None:
            return node.is_dir  # show the expand arrow before scanning
        return len(node.children) > 0

    def canFetchMore(self, parent: QtCore.QModelIndex) -> bool:
        node = self._node(parent)
        return node.is_dir and node.children is None

    def fetchMore(self, parent: QtCore.QModelIndex):
        node = self._node(parent)
        if not node.is_dir or node.children is not None:
            return
        children = node.scan()
        if children:
            self.beginInsertRows(parent, 0, len(children) - 1)
            node.children = children
            self.endInsertRows()
        else:
            node.children = children

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
        if not index.isValid():
            return QtCore.Qt.ItemFlag.NoItemFlags
        return (
            QtCore.Qt.ItemFlag.ItemIsEnabled
            | QtCore.Qt.ItemFlag.ItemIsSelectable
            | QtCore.Qt.ItemFlag.ItemIsDragEnabled
        )

    def data(self, index: QtCore.QModelIndex, role: int = _ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        node: _Node = index.internalPointer()
        if role == _ItemDataRole.DisplayRole:
            return node.path.name
        if role == _ItemDataRole.DecorationRole:
            return self._dir_icon if node.is_dir else self._file_icon
        if role == _ItemDataRole.SizeHintRole:
            return QtCore.QSize(18, 16)
        if role == _ItemDataRole.ToolTipRole:
            return path_tooltip(node.path)
        return None

    def refresh(self, path: Path | str):
        """Rescan the directory at `path` if it is already listed."""
        node = self._find_scanned_dir(Path(path))
        if node is None:
            return
        parent_index = (
            QtCore.QModelIndex()
            if node is self._root
            else self.createIndex(node.row(), 0, node)
        )
        new_children = node.scan()
        new_paths = {n.path for n in new_children}
        old_children = node.children
        # remove deleted entries (from the end to keep the row numbers valid)
        for row in reversed(range(len(old_children))):
            if old_children[row].path not in new_paths:
                self.beginRemoveRows(parent_index, row, row)
                del old_children[row]
                self.endRemoveRows()
        # insert new entries at the sorted positions
        old_paths = {n.path for n in old_children}
        for child in new_children:
            if child.path in old_paths:
                continue
            row = bisect_left([n.sort_key for n in old_children], child.sort_key)
            self.beginInsertRows(parent_index, row, row)
            old_children.insert(row, child)
            self.endInsertRows()

    def _find_scanned_dir(self, path: Path) -> _Node | None:
        try:
            rel_parts = path.relative_to(self._root.path).parts
        except ValueError:
            return None
        node = self._root
        for part in rel_parts:
            if node.children is None:
                return None
            for child in node.children:
                if child.path.name == part:
                    node = child
                    break
            else:
                return None
        if node.children is None:
            return None
        return node
