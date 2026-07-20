"""Core-owned tables: entities, relationships, and the plugin migration ledger."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from skrybe_studio.core.storage.base import Base


class EntityRecord(Base):
    """Persisted row for a shared, globally addressable `Entity`."""

    __tablename__ = "core_entities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(512))
    plugin_owner: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class RelationshipRecord(Base):
    """Persisted row for a directed, typed `Relationship` between two entities."""

    __tablename__ = "core_relationships"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core_entities.id"), index=True)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core_entities.id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(128), index=True)
    plugin_owner: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class PluginMigrationRecord(Base):
    """Ledger row recording that a named plugin migration has been applied."""

    __tablename__ = "core_plugin_migrations"
    __table_args__ = (UniqueConstraint("plugin_id", "migration_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plugin_id: Mapped[str] = mapped_column(String(256), index=True)
    migration_name: Mapped[str] = mapped_column(String(256))
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
