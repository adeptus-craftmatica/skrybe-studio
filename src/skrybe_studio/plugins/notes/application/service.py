"""Keeps the plugin-owned `Note` row and the shared `Entity` in sync, and publishes events."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from skrybe_studio.core.entities.service import EntityService
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.notes.application.events import NoteCreated, NoteDeleted, NoteUpdated
from skrybe_studio.plugins.notes.domain.note import ENTITY_TYPE, PLUGIN_ID, Note
from skrybe_studio.plugins.notes.infrastructure.repository import NoteRepository

logger = logging.getLogger(__name__)


class NotesService:
    def __init__(
        self, repository: NoteRepository, entities: EntityService, events: EventBus
    ) -> None:
        self._repository = repository
        self._entities = entities
        self._events = events

    def create_note(self, title: str, *, body: str = "", tags: tuple[str, ...] = ()) -> Note:
        now = datetime.now(UTC)
        note_id = uuid4()
        self._entities.create(
            entity_type=ENTITY_TYPE, title=title, plugin_owner=PLUGIN_ID, entity_id=note_id
        )
        note = Note(id=note_id, title=title, body=body, tags=tags, created_at=now, updated_at=now)
        self._repository.add(note)
        logger.info("Created note '%s' (%s)", title, note_id)
        self._events.publish(NoteCreated(note_id=note_id, title=title))
        return note

    def rename_note(self, note_id: UUID, title: str) -> Note | None:
        note = self._repository.update(note_id, title=title)
        if note is None:
            return None
        self._entities.rename(note_id, title)
        self._events.publish(NoteUpdated(note_id=note_id))
        return note

    def update_note(
        self,
        note_id: UUID,
        *,
        title: str | None = None,
        body: str | None = None,
        tags: tuple[str, ...] | None = None,
    ) -> Note | None:
        """Combined editor-autosave update: one write, one event, regardless of how many fields changed."""
        note = self._repository.update(note_id, title=title, body=body, tags=tags)
        if note is None:
            return None
        if title is not None:
            self._entities.rename(note_id, title)
        self._events.publish(NoteUpdated(note_id=note_id))
        return note

    def archive_note(self, note_id: UUID) -> bool:
        archived = self._repository.archive(note_id)
        if archived:
            self._events.publish(NoteUpdated(note_id=note_id))
        return archived

    def delete_note(self, note_id: UUID) -> bool:
        deleted = self._repository.delete(note_id)
        if deleted:
            self._entities.soft_delete(note_id)
            self._events.publish(NoteDeleted(note_id=note_id))
        return deleted

    def get_note(self, note_id: UUID) -> Note | None:
        return self._repository.get(note_id)

    def list_notes(self, *, include_archived: bool = False) -> list[Note]:
        return self._repository.list(include_archived=include_archived)

    def search_notes(self, query: str) -> list[Note]:
        return self._repository.search(query)
