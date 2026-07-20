"""Typed events published by the Story Bible plugin's application services."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from skrybe_studio.core.contracts.event import Event


@dataclass(frozen=True, slots=True)
class EntityTypeCreated(Event):
    entity_type_id: UUID
    type_key: str


@dataclass(frozen=True, slots=True)
class EntityTypeArchived(Event):
    entity_type_id: UUID


@dataclass(frozen=True, slots=True)
class FieldDefinitionChanged(Event):
    entity_type_id: UUID
    field_id: UUID


@dataclass(frozen=True, slots=True)
class EntityCreated(Event):
    entity_id: UUID
    entity_type_id: UUID
    primary_name: str


@dataclass(frozen=True, slots=True)
class EntityRenamed(Event):
    entity_id: UUID
    primary_name: str


@dataclass(frozen=True, slots=True)
class EntityMetadataChanged(Event):
    entity_id: UUID


@dataclass(frozen=True, slots=True)
class EntityArchived(Event):
    entity_id: UUID


@dataclass(frozen=True, slots=True)
class EntityRestored(Event):
    entity_id: UUID


@dataclass(frozen=True, slots=True)
class FieldValueChanged(Event):
    entity_id: UUID
    field_id: UUID


@dataclass(frozen=True, slots=True)
class EntitySelectionChanged(Event):
    """UI-only: which entity is currently selected in the Worldbuilding workspace."""

    entity_id: UUID | None
