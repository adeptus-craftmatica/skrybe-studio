"""Lists notes in the current project and lets the user create, search, and delete them."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from skrybe_studio.core.contracts.event import Event
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.notes.application.events import (
    NoteCreated,
    NoteDeleted,
    NoteSelectionChanged,
    NoteUpdated,
)

if TYPE_CHECKING:
    from skrybe_studio.plugins.notes.plugin import NotesPlugin


class NotesBrowserPanel(QWidget):
    def __init__(self, plugin: NotesPlugin, events: EventBus) -> None:
        super().__init__()
        self._plugin = plugin
        self._events = events

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search notes…")
        self._search.textChanged.connect(self._refresh)

        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_selection_changed)

        new_button = QPushButton("New Note")
        new_button.setObjectName("primary")
        new_button.clicked.connect(self._on_new_note)
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self._on_delete_note)

        button_row = QHBoxLayout()
        button_row.addWidget(new_button)
        button_row.addWidget(delete_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._search)
        layout.addWidget(self._list)
        layout.addLayout(button_row)

        events.subscribe(NoteCreated, self._on_note_changed)
        events.subscribe(NoteUpdated, self._on_note_changed)
        events.subscribe(NoteDeleted, self._on_note_changed)

        self._refresh("")

    def _on_note_changed(self, _event: Event) -> None:
        self._refresh(self._search.text())

    def _refresh(self, query: str) -> None:
        self._list.clear()
        if self._plugin.service is None:
            return
        notes = (
            self._plugin.service.search_notes(query)
            if query.strip()
            else self._plugin.service.list_notes()
        )
        for note in notes:
            item = QListWidgetItem(f"{note.title}   ({note.word_count} words)")
            item.setData(Qt.ItemDataRole.UserRole, note.id)
            self._list.addItem(item)

    def _on_selection_changed(self) -> None:
        item = self._list.currentItem()
        note_id: UUID | None = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        self._plugin.set_selected_note(note_id)
        self._events.publish(NoteSelectionChanged(note_id=note_id))

    def _on_new_note(self) -> None:
        if self._plugin.service is None:
            return
        self._plugin.service.create_note("Untitled Note")

    def _on_delete_note(self) -> None:
        item = self._list.currentItem()
        if item is None or self._plugin.service is None:
            return
        self._plugin.service.delete_note(item.data(Qt.ItemDataRole.UserRole))
