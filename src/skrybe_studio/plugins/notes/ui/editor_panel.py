"""A simple plain-text note editor: title, tags, body, live word count, debounced autosave."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget

from skrybe_studio.core.contracts.event import Event
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.notes.application.events import NoteSelectionChanged

if TYPE_CHECKING:
    from skrybe_studio.plugins.notes.plugin import NotesPlugin

AUTOSAVE_DELAY_MS = 600


class NoteEditorPanel(QWidget):
    def __init__(self, plugin: NotesPlugin, events: EventBus) -> None:
        super().__init__()
        self._plugin = plugin
        self._current_note_id: UUID | None = None
        self._loading = False

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Note title")
        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("Tags, comma separated")
        self._body_edit = QPlainTextEdit()
        self._body_edit.setPlaceholderText("Start writing…")
        self._word_count_label = QLabel("0 words")
        self._word_count_label.setObjectName("muted")

        layout = QVBoxLayout(self)
        layout.addWidget(self._title_edit)
        layout.addWidget(self._tags_edit)
        layout.addWidget(self._body_edit)
        layout.addWidget(self._word_count_label)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(AUTOSAVE_DELAY_MS)
        self._autosave_timer.timeout.connect(self._save)

        self._title_edit.textEdited.connect(self._schedule_save)
        self._tags_edit.textEdited.connect(self._schedule_save)
        self._body_edit.textChanged.connect(self._on_body_changed)

        events.subscribe(NoteSelectionChanged, self._on_selection_changed)
        self.setEnabled(False)

    def _on_selection_changed(self, event: Event) -> None:
        if isinstance(event, NoteSelectionChanged):
            self._load_note(event.note_id)

    def _load_note(self, note_id: UUID | None) -> None:
        self._save()
        self._current_note_id = note_id
        if note_id is None or self._plugin.service is None:
            self.setEnabled(False)
            return
        note = self._plugin.service.get_note(note_id)
        if note is None:
            self.setEnabled(False)
            return
        self.setEnabled(True)
        self._loading = True
        self._title_edit.setText(note.title)
        self._tags_edit.setText(", ".join(note.tags))
        self._body_edit.setPlainText(note.body)
        self._update_word_count(note.body)
        self._loading = False

    def _on_body_changed(self) -> None:
        self._update_word_count(self._body_edit.toPlainText())
        self._schedule_save()

    def _update_word_count(self, body: str) -> None:
        count = len([word for word in body.split() if word])
        self._word_count_label.setText(f"{count} word{'s' if count != 1 else ''}")

    def _schedule_save(self) -> None:
        if self._loading:
            return
        self._autosave_timer.start()

    def _save(self) -> None:
        self._autosave_timer.stop()
        if self._current_note_id is None or self._plugin.service is None:
            return
        title = self._title_edit.text().strip() or "Untitled Note"
        tags = tuple(t.strip() for t in self._tags_edit.text().split(",") if t.strip())
        body = self._body_edit.toPlainText()
        self._plugin.service.update_note(self._current_note_id, title=title, body=body, tags=tags)
