"""Typed events published by the Notes plugin."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from skrybe_studio.core.contracts.event import Event


@dataclass(frozen=True, slots=True)
class NoteCreated(Event):
    note_id: UUID
    title: str


@dataclass(frozen=True, slots=True)
class NoteUpdated(Event):
    note_id: UUID


@dataclass(frozen=True, slots=True)
class NoteDeleted(Event):
    note_id: UUID


@dataclass(frozen=True, slots=True)
class NoteSelectionChanged(Event):
    """UI-only event: which note the Notes browser panel currently has selected."""

    note_id: UUID | None
