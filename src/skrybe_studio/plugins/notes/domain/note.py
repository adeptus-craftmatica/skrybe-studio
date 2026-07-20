"""The Notes plugin's domain model. `Note.id` is also its shared `Entity` ID."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

ENTITY_TYPE = "notes.note"
PLUGIN_ID = "com.adeptus-craftmatica.skrybe.notes"


@dataclass(frozen=True, slots=True)
class Note:
    id: UUID
    title: str
    body: str
    tags: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    @property
    def word_count(self) -> int:
        return len([word for word in self.body.split() if word])
