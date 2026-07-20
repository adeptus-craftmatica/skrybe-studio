"""The binder panel: manuscript picker, hierarchy tree, and node-management toolbar."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from skrybe_studio.core.contracts.event import Event
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.manuscript.application.events import (
    ManuscriptCreated,
    NodeArchived,
    NodeCreated,
    NodeMetadataChanged,
    NodeMoved,
    NodeRenamed,
    NodeRestored,
    NodeSelectionChanged,
)
from skrybe_studio.plugins.manuscript.domain.enums import ALLOWED_CHILD_TYPES, ManuscriptNodeType
from skrybe_studio.plugins.manuscript.domain.exceptions import ManuscriptError
from skrybe_studio.plugins.manuscript.ui.binder.model import ManuscriptTreeModel
from skrybe_studio.plugins.manuscript.ui.dialogs.new_manuscript_dialog import NewManuscriptDialog

if TYPE_CHECKING:
    from skrybe_studio.plugins.manuscript.plugin import ManuscriptPlugin

logger = logging.getLogger(__name__)

_CREATABLE_TYPES = (
    ManuscriptNodeType.FOLDER,
    ManuscriptNodeType.PART,
    ManuscriptNodeType.CHAPTER,
    ManuscriptNodeType.SCENE,
    ManuscriptNodeType.DOCUMENT,
)

_TYPE_LABELS = {
    ManuscriptNodeType.FOLDER: "Folder",
    ManuscriptNodeType.PART: "Part",
    ManuscriptNodeType.CHAPTER: "Chapter",
    ManuscriptNodeType.SCENE: "Scene",
    ManuscriptNodeType.DOCUMENT: "Document",
}

_REFRESHING_EVENTS = (
    NodeCreated,
    NodeRenamed,
    NodeMoved,
    NodeArchived,
    NodeRestored,
    NodeMetadataChanged,
)


class BinderPanel(QWidget):
    def __init__(self, plugin: ManuscriptPlugin, events: EventBus) -> None:
        super().__init__()
        self._plugin = plugin
        self._events = events
        self._model: ManuscriptTreeModel | None = None

        self._manuscript_combo = QComboBox()
        self._manuscript_combo.currentIndexChanged.connect(self._on_manuscript_changed)
        new_manuscript_button = QPushButton("New…")
        new_manuscript_button.clicked.connect(self._on_new_manuscript)

        manuscript_row = QHBoxLayout()
        manuscript_row.addWidget(self._manuscript_combo, stretch=1)
        manuscript_row.addWidget(new_manuscript_button)

        self._tree = QTreeView()
        self._tree.setHeaderHidden(True)
        self._tree.setDragEnabled(True)
        self._tree.setAcceptDrops(True)
        self._tree.setDropIndicatorShown(True)
        self._tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.setEditTriggers(
            QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.SelectedClicked
        )

        button_row = QHBoxLayout()
        new_node_button = QPushButton("New Node…")
        new_node_button.setObjectName("primary")
        new_node_button.clicked.connect(self._on_new_node_menu)
        archive_button = QPushButton("Archive")
        archive_button.clicked.connect(self._on_archive_selected)
        button_row.addWidget(new_node_button)
        button_row.addWidget(archive_button)

        layout = QVBoxLayout(self)
        layout.addLayout(manuscript_row)
        layout.addWidget(self._tree)
        layout.addLayout(button_row)

        for event_type in _REFRESHING_EVENTS:
            events.subscribe(event_type, self._on_hierarchy_changed)
        events.subscribe(ManuscriptCreated, self._on_manuscript_created)

        plugin.set_binder_panel(self)
        self._refresh_manuscript_list(select_manuscript_id=None)

    # --- manuscript selection ---------------------------------------------------

    def _refresh_manuscript_list(self, *, select_manuscript_id: UUID | None) -> None:
        if self._plugin.hierarchy is None:
            return
        manuscripts = self._plugin.hierarchy.list_manuscripts()
        self._manuscript_combo.blockSignals(True)
        self._manuscript_combo.clear()
        for manuscript in manuscripts:
            self._manuscript_combo.addItem(manuscript.title, manuscript.id)
        self._manuscript_combo.blockSignals(False)

        target_id = select_manuscript_id or (manuscripts[0].id if manuscripts else None)
        if target_id is not None:
            index = self._manuscript_combo.findData(target_id)
            if index >= 0:
                self._manuscript_combo.setCurrentIndex(index)
        self._load_manuscript(target_id)

    def _on_manuscript_created(self, event: Event) -> None:
        if isinstance(event, ManuscriptCreated):
            self._refresh_manuscript_list(select_manuscript_id=event.manuscript_id)

    def _on_manuscript_changed(self, index: int) -> None:
        manuscript_id = self._manuscript_combo.itemData(index)
        self._load_manuscript(manuscript_id)

    def _load_manuscript(self, manuscript_id: UUID | None) -> None:
        if manuscript_id is None or self._plugin.hierarchy is None:
            self._model = None
            self._tree.setModel(None)
            return
        self._model = ManuscriptTreeModel(self._plugin.hierarchy, manuscript_id)
        self._tree.setModel(self._model)
        self._tree.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._tree.expandToDepth(0)

    def _on_new_manuscript(self) -> None:
        if self._plugin.hierarchy is None:
            return
        dialog = NewManuscriptDialog(self)
        if dialog.exec() == NewManuscriptDialog.DialogCode.Accepted:
            self._plugin.hierarchy.create_manuscript(dialog.title(), dialog.template())

    # --- refresh with state preservation ---------------------------------------

    def _on_hierarchy_changed(self, _event: Event) -> None:
        self._refresh_preserving_state()

    def _refresh_preserving_state(self) -> None:
        if self._model is None:
            return
        expanded_ids = self._collect_expanded_ids(QModelIndex())
        selected_id = self._plugin.selected_node_id
        self._model.refresh()
        self._restore_expanded_ids(QModelIndex(), expanded_ids)
        if selected_id is not None:
            index = self._model.index_for_node_id(selected_id)
            if index.isValid():
                self._tree.setCurrentIndex(index)

    def _collect_expanded_ids(self, parent: QModelIndex) -> set[UUID]:
        if self._model is None:
            return set()
        expanded: set[UUID] = set()
        for row in range(self._model.rowCount(parent)):
            index = self._model.index(row, 0, parent)
            if self._tree.isExpanded(index):
                node = self._model.node_for_index(index)
                if node is not None:
                    expanded.add(node.id)
                expanded |= self._collect_expanded_ids(index)
        return expanded

    def _restore_expanded_ids(self, parent: QModelIndex, expanded_ids: set[UUID]) -> None:
        if self._model is None:
            return
        for row in range(self._model.rowCount(parent)):
            index = self._model.index(row, 0, parent)
            node = self._model.node_for_index(index)
            if node is not None and node.id in expanded_ids:
                self._tree.setExpanded(index, True)
            self._restore_expanded_ids(index, expanded_ids)

    # --- selection -----------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        node_id = self._current_node_id()
        self._plugin.set_selected_node(node_id)
        self._events.publish(NodeSelectionChanged(node_id=node_id))

    def _current_node_id(self) -> UUID | None:
        if self._model is None:
            return None
        index = self._tree.currentIndex()
        node = self._model.node_for_index(index)
        return node.id if node is not None else None

    def start_rename_selected(self) -> None:
        index = self._tree.currentIndex()
        if index.isValid():
            self._tree.edit(index)

    def reveal_node(self, node_id: UUID) -> None:
        if self._model is None:
            return
        index = self._model.index_for_node_id(node_id)
        if not index.isValid():
            return
        parent = index.parent()
        while parent.isValid():
            self._tree.setExpanded(parent, True)
            parent = parent.parent()
        self._tree.setCurrentIndex(index)
        self._tree.scrollTo(index)

    # --- node creation / deletion ------------------------------------------------

    def _on_new_node_menu(self) -> None:
        if self._model is None or self._plugin.hierarchy is None:
            return
        parent_node = self._model.node_for_index(self._tree.currentIndex())
        parent_type = (
            parent_node.node_type if parent_node is not None else ManuscriptNodeType.MANUSCRIPT
        )
        allowed = ALLOWED_CHILD_TYPES.get(parent_type, frozenset())

        menu = QMenu(self)
        for node_type in _CREATABLE_TYPES:
            action = menu.addAction(f"New {_TYPE_LABELS[node_type]}")
            action.setEnabled(node_type in allowed)
            action.triggered.connect(lambda _checked, nt=node_type: self._create_node(nt))
        menu.exec(self.mapToGlobal(self.rect().center()))

    def _create_node(self, node_type: ManuscriptNodeType) -> None:
        if self._model is None or self._plugin.hierarchy is None:
            return
        parent_node = self._model.node_for_index(self._tree.currentIndex())
        parent_id = parent_node.id if parent_node is not None else self._model.manuscript_id
        try:
            self._plugin.hierarchy.create_node(
                parent_id, node_type, f"New {_TYPE_LABELS[node_type]}"
            )
        except ManuscriptError as exc:
            QMessageBox.warning(self, "New Node", str(exc))

    def _on_archive_selected(self) -> None:
        node_id = self._current_node_id()
        if node_id is None or self._plugin.hierarchy is None:
            return
        self._plugin.hierarchy.archive_node(node_id)

    def _on_context_menu(self, position) -> None:
        if self._model is None:
            return
        index = self._tree.indexAt(position)
        node = self._model.node_for_index(index)
        menu = QMenu(self)
        if node is not None:
            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self._tree.edit(index))
            duplicate_action = menu.addAction("Duplicate")
            duplicate_action.triggered.connect(lambda: self._duplicate_node(node.id))
            menu.addSeparator()
            archive_action = menu.addAction("Archive")
            archive_action.triggered.connect(lambda: self._archive_node(node.id))
            menu.addSeparator()
        new_menu = menu.addMenu("New Node")
        parent_type = node.node_type if node is not None else ManuscriptNodeType.MANUSCRIPT
        allowed = ALLOWED_CHILD_TYPES.get(parent_type, frozenset())
        for node_type in _CREATABLE_TYPES:
            action = new_menu.addAction(f"New {_TYPE_LABELS[node_type]}")
            action.setEnabled(node_type in allowed)
            action.triggered.connect(lambda _checked, nt=node_type: self._create_node(nt))
        menu.exec(self._tree.viewport().mapToGlobal(position))

    def _duplicate_node(self, node_id: UUID) -> None:
        if self._plugin.hierarchy is not None:
            self._plugin.hierarchy.duplicate_node(node_id)

    def _archive_node(self, node_id: UUID) -> None:
        if self._plugin.hierarchy is not None:
            self._plugin.hierarchy.archive_node(node_id)
