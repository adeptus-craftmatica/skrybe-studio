"""Manuscript-local search: current document, current subtree, or whole manuscript."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from skrybe_studio.plugins.manuscript.plugin import ManuscriptPlugin

_SCOPE_MANUSCRIPT = "manuscript"
_SCOPE_SUBTREE = "subtree"
_SCOPE_DOCUMENT = "document"


class ManuscriptSearchPanel(QWidget):
    def __init__(self, plugin: ManuscriptPlugin) -> None:
        super().__init__()
        self._plugin = plugin

        self._query_edit = QLineEdit()
        self._query_edit.setPlaceholderText("Search manuscript…")
        self._query_edit.returnPressed.connect(self._on_search)

        self._scope_combo = QComboBox()
        self._scope_combo.addItem("Whole Manuscript", _SCOPE_MANUSCRIPT)
        self._scope_combo.addItem("Current Subtree", _SCOPE_SUBTREE)
        self._scope_combo.addItem("Current Document", _SCOPE_DOCUMENT)

        search_button = QPushButton("Search")
        search_button.setObjectName("primary")
        search_button.clicked.connect(self._on_search)

        top_row = QHBoxLayout()
        top_row.addWidget(self._query_edit, stretch=1)
        top_row.addWidget(self._scope_combo)
        top_row.addWidget(search_button)

        self._results = QListWidget()
        self._results.itemActivated.connect(self._on_result_activated)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addWidget(self._results)

    def _on_search(self) -> None:
        query = self._query_edit.text().strip()
        self._results.clear()
        if not query or self._plugin.search_provider is None:
            return

        scope = self._scope_combo.currentData()
        manuscript_id = None
        node_filter: set | None = None
        selected = self._plugin.selected_node_id
        if selected is not None and self._plugin.hierarchy is not None:
            selected_node = self._plugin.hierarchy.get_node(selected)
            if selected_node is not None:
                manuscript_id = selected_node.manuscript_id
                if scope == _SCOPE_SUBTREE:
                    node_filter = {n.id for n in self._plugin.hierarchy.list_subtree(selected)}
                elif scope == _SCOPE_DOCUMENT:
                    node_filter = {selected}

        results = self._plugin.search_provider.search_scoped(query, manuscript_id=manuscript_id)
        if node_filter is not None:
            results = [result for result in results if result.entity_id in node_filter]

        for result in results:
            item = QListWidgetItem(f"{result.title}   —   {result.snippet[:60]}")
            item.setData(Qt.ItemDataRole.UserRole, result.entity_id)
            self._results.addItem(item)

    def _on_result_activated(self, item: QListWidgetItem) -> None:
        node_id = item.data(Qt.ItemDataRole.UserRole)
        if node_id is not None:
            self._plugin.reveal_and_open(node_id)
