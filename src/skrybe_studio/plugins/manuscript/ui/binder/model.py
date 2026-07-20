"""A `QAbstractItemModel` over one manuscript's hierarchy.

The database (via `HierarchyService`) is the source of truth - this
model caches a plain tree of `_TreeItem`s for Qt's index/parent/rowCount
machinery, and rebuilds itself from the repository after every mutation
rather than maintaining independent authoritative state. Simpler and far
less error-prone than fine-grained `beginMoveRows`/`endMoveRows`
bookkeeping, at the cost of losing row-move animations - an acceptable
trade for a binder this size.
"""

from __future__ import annotations

import logging
from uuid import UUID

from PySide6.QtCore import QAbstractItemModel, QMimeData, QModelIndex, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyle

from skrybe_studio.plugins.manuscript.application.hierarchy_service import HierarchyService
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType
from skrybe_studio.plugins.manuscript.domain.exceptions import (
    CyclicHierarchyError,
    InvalidHierarchyError,
    NodeNotFoundError,
)
from skrybe_studio.plugins.manuscript.domain.models import ManuscriptNode

logger = logging.getLogger(__name__)

NODE_MIME_TYPE = "application/x-skrybe-manuscript-node"
NODE_ID_ROLE = Qt.ItemDataRole.UserRole + 1

# A single reusable "invalid/root" index, so it's never constructed inline
# as a mutable-looking default argument.
_ROOT_INDEX = QModelIndex()

_CONTAINER_ICON_TYPES = frozenset(
    {ManuscriptNodeType.FOLDER, ManuscriptNodeType.PART, ManuscriptNodeType.CHAPTER}
)


def _icon_for(node_type: ManuscriptNodeType) -> QIcon:
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return QIcon()
    style = app.style()
    if style is None:
        return QIcon()
    if node_type is ManuscriptNodeType.MANUSCRIPT:
        pixmap = QStyle.StandardPixmap.SP_DriveHDIcon
    elif node_type in _CONTAINER_ICON_TYPES:
        pixmap = QStyle.StandardPixmap.SP_DirIcon
    else:
        pixmap = QStyle.StandardPixmap.SP_FileIcon
    return style.standardIcon(pixmap)


class _TreeItem:
    __slots__ = ("children", "node", "parent_item")

    def __init__(self, node: ManuscriptNode, parent_item: _TreeItem | None) -> None:
        self.node = node
        self.parent_item = parent_item
        self.children: list[_TreeItem] = []

    def row(self) -> int:
        if self.parent_item is None:
            return 0
        return self.parent_item.children.index(self)


class ManuscriptTreeModel(QAbstractItemModel):
    def __init__(self, hierarchy: HierarchyService, manuscript_id: UUID, parent=None) -> None:
        super().__init__(parent)
        self._hierarchy = hierarchy
        self._manuscript_id = manuscript_id
        self._root_item: _TreeItem | None = None
        self.refresh()

    @property
    def manuscript_id(self) -> UUID:
        return self._manuscript_id

    def refresh(self) -> None:
        self.beginResetModel()
        root_node = self._hierarchy.get_node(self._manuscript_id)
        self._root_item = self._build_item(root_node, None) if root_node is not None else None
        self.endResetModel()

    def _build_item(self, node: ManuscriptNode, parent_item: _TreeItem | None) -> _TreeItem:
        item = _TreeItem(node, parent_item)
        for child in self._hierarchy.list_children(node.id):
            item.children.append(self._build_item(child, item))
        return item

    # --- required overrides --------------------------------------------------

    def index(self, row: int, column: int, parent: QModelIndex = _ROOT_INDEX) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parent_item = parent.internalPointer() if parent.isValid() else self._root_item
        if parent_item is None or row >= len(parent_item.children):
            return QModelIndex()
        return self.createIndex(row, column, parent_item.children[row])

    def parent(self, index: QModelIndex) -> QModelIndex:  # type: ignore[override]
        if not index.isValid():
            return QModelIndex()
        item: _TreeItem = index.internalPointer()
        parent_item = item.parent_item
        if parent_item is None or parent_item is self._root_item:
            return QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent: QModelIndex = _ROOT_INDEX) -> int:
        if self._root_item is None:
            return 0
        parent_item = parent.internalPointer() if parent.isValid() else self._root_item
        return len(parent_item.children)

    def columnCount(self, parent: QModelIndex = _ROOT_INDEX) -> int:
        return 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        item: _TreeItem = index.internalPointer()
        node = item.node
        if role == Qt.ItemDataRole.EditRole:
            return node.title
        if role == Qt.ItemDataRole.DisplayRole:
            suffix = f"  ({node.word_count} words)" if node.is_text_bearing else ""
            return f"{node.title}{suffix}"
        if role == Qt.ItemDataRole.DecorationRole:
            return _icon_for(node.node_type)
        if role == Qt.ItemDataRole.ToolTipRole:
            parts = [node.synopsis] if node.synopsis else []
            if not node.include_in_compile:
                parts.append("Excluded from compile")
            return "\n".join(parts) or None
        if role == Qt.ItemDataRole.FontRole and not node.include_in_compile:
            from PySide6.QtGui import QFont

            font = QFont()
            font.setItalic(True)
            return font
        if role == NODE_ID_ROLE:
            return node.id
        return None

    def setData(
        self, index: QModelIndex, value: object, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        title = str(value).strip()
        if not title:
            return False
        item: _TreeItem = index.internalPointer()
        self._hierarchy.rename_node(item.node.id, title)
        self.refresh()
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.ItemIsDropEnabled
        item: _TreeItem = index.internalPointer()
        flags = (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsDragEnabled
        )
        if item.node.is_container:
            flags |= Qt.ItemFlag.ItemIsDropEnabled
        return flags

    # --- lookups for the panel -------------------------------------------------

    def node_for_index(self, index: QModelIndex) -> ManuscriptNode | None:
        if not index.isValid():
            return None
        item: _TreeItem = index.internalPointer()
        return item.node

    def index_for_node_id(self, node_id: UUID, parent: QModelIndex = _ROOT_INDEX) -> QModelIndex:
        parent_item = parent.internalPointer() if parent.isValid() else self._root_item
        if parent_item is None:
            return QModelIndex()
        for row, child in enumerate(parent_item.children):
            if child.node.id == node_id:
                return self.index(row, 0, parent)
            found = self.index_for_node_id(node_id, self.index(row, 0, parent))
            if found.isValid():
                return found
        return QModelIndex()

    # --- drag and drop -----------------------------------------------------------

    def mimeTypes(self) -> list[str]:
        return [NODE_MIME_TYPE]

    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:
        node_ids = {str(index.internalPointer().node.id) for index in indexes if index.isValid()}
        mime = QMimeData()
        mime.setData(NODE_MIME_TYPE, ",".join(node_ids).encode("utf-8"))
        return mime

    def canDropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        return data.hasFormat(NODE_MIME_TYPE)

    def dropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if not data.hasFormat(NODE_MIME_TYPE):
            return False
        raw = bytes(data.data(NODE_MIME_TYPE).data()).decode("utf-8")
        node_ids = [UUID(part) for part in raw.split(",") if part]
        parent_item = parent.internalPointer() if parent.isValid() else self._root_item
        if parent_item is None or not node_ids:
            return False

        new_parent_id = parent_item.node.id
        siblings = parent_item.children
        if row < 0 or row > len(siblings):
            before_id = siblings[-1].node.id if siblings else None
            after_id = None
        else:
            before_id = siblings[row - 1].node.id if row > 0 else None
            after_id = siblings[row].node.id if row < len(siblings) else None

        moved_any = False
        for node_id in node_ids:
            try:
                self._hierarchy.move_node(
                    node_id, new_parent_id, before_id=before_id, after_id=after_id
                )
                moved_any = True
            except (InvalidHierarchyError, CyclicHierarchyError, NodeNotFoundError) as exc:
                logger.info("Rejected drop of %s onto %s: %s", node_id, new_parent_id, exc)
        if moved_any:
            self.refresh()
        return moved_any
