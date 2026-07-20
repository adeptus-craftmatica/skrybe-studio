"""Typed events published by the Manuscript plugin.

Payloads carry stable IDs and small, meaningful metadata only - never a
mutable ORM instance, and never on every keystroke (`DocumentContentChanged`
fires after a debounced save commits, not per edit).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from skrybe_studio.core.contracts.event import Event


@dataclass(frozen=True, slots=True)
class ManuscriptCreated(Event):
    manuscript_id: UUID
    title: str


@dataclass(frozen=True, slots=True)
class ManuscriptRenamed(Event):
    manuscript_id: UUID
    title: str


@dataclass(frozen=True, slots=True)
class ManuscriptArchived(Event):
    manuscript_id: UUID


@dataclass(frozen=True, slots=True)
class NodeCreated(Event):
    node_id: UUID
    manuscript_id: UUID
    parent_id: UUID
    node_type: str


@dataclass(frozen=True, slots=True)
class NodeRenamed(Event):
    node_id: UUID
    title: str


@dataclass(frozen=True, slots=True)
class NodeMoved(Event):
    node_id: UUID
    new_parent_id: UUID


@dataclass(frozen=True, slots=True)
class NodeMetadataChanged(Event):
    node_id: UUID


@dataclass(frozen=True, slots=True)
class NodeArchived(Event):
    node_id: UUID
    affected_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class NodeRestored(Event):
    node_id: UUID
    affected_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class DocumentContentChanged(Event):
    node_id: UUID
    word_count: int


@dataclass(frozen=True, slots=True)
class SnapshotCreated(Event):
    snapshot_id: UUID
    node_id: UUID


@dataclass(frozen=True, slots=True)
class SnapshotRestored(Event):
    node_id: UUID
    snapshot_id: UUID


@dataclass(frozen=True, slots=True)
class CompileStarted(Event):
    manuscript_id: UUID


@dataclass(frozen=True, slots=True)
class CompileCompleted(Event):
    manuscript_id: UUID
    warning_count: int


@dataclass(frozen=True, slots=True)
class CompileFailed(Event):
    manuscript_id: UUID
    message: str


@dataclass(frozen=True, slots=True)
class NodeSelectionChanged(Event):
    """UI-only event: which node the binder panel currently has selected."""

    node_id: UUID | None
