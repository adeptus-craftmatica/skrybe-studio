"""CRUD service for the shared `Entity` contract, with soft deletion."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from skrybe_studio.core.contracts.entity import Entity
from skrybe_studio.core.storage.database import Database
from skrybe_studio.core.storage.models import EntityRecord

logger = logging.getLogger(__name__)


def _to_entity(record: EntityRecord) -> Entity:
    return Entity(
        id=record.id,
        entity_type=record.entity_type,
        title=record.title,
        plugin_owner=record.plugin_owner,
        created_at=record.created_at,
        updated_at=record.updated_at,
        deleted_at=record.deleted_at,
        metadata=dict(record.metadata_json or {}),
    )


class EntityService:
    """Creates, queries, and soft-deletes shared entities for a project."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def create(
        self,
        *,
        entity_type: str,
        title: str,
        plugin_owner: str,
        metadata: dict[str, Any] | None = None,
        entity_id: UUID | None = None,
    ) -> Entity:
        now = datetime.now(UTC)
        entity = Entity(
            id=entity_id or uuid4(),
            entity_type=entity_type,
            title=title,
            plugin_owner=plugin_owner,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        with self._database.session() as session:
            session.add(
                EntityRecord(
                    id=entity.id,
                    entity_type=entity.entity_type,
                    title=entity.title,
                    plugin_owner=entity.plugin_owner,
                    created_at=entity.created_at,
                    updated_at=entity.updated_at,
                    deleted_at=None,
                    metadata_json=dict(entity.metadata),
                )
            )
        logger.debug("Created entity %s (%s) owned by %s", entity.id, entity_type, plugin_owner)
        return entity

    def get(self, entity_id: UUID, *, include_deleted: bool = False) -> Entity | None:
        with self._database.session() as session:
            record = session.get(EntityRecord, entity_id)
            if record is None:
                return None
            if record.deleted_at is not None and not include_deleted:
                return None
            return _to_entity(record)

    def list(
        self,
        *,
        entity_type: str | None = None,
        plugin_owner: str | None = None,
        include_deleted: bool = False,
    ) -> list[Entity]:
        with self._database.session() as session:
            stmt = select(EntityRecord)
            if entity_type is not None:
                stmt = stmt.where(EntityRecord.entity_type == entity_type)
            if plugin_owner is not None:
                stmt = stmt.where(EntityRecord.plugin_owner == plugin_owner)
            if not include_deleted:
                stmt = stmt.where(EntityRecord.deleted_at.is_(None))
            return [_to_entity(record) for record in session.scalars(stmt)]

    def rename(self, entity_id: UUID, title: str) -> Entity | None:
        return self.update(entity_id, title=title)

    def update(
        self,
        entity_id: UUID,
        *,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Entity | None:
        with self._database.session() as session:
            record = session.get(EntityRecord, entity_id)
            if record is None:
                return None
            if title is not None:
                record.title = title
            if metadata is not None:
                record.metadata_json = metadata
            record.updated_at = datetime.now(UTC)
            session.flush()
            return _to_entity(record)

    def soft_delete(self, entity_id: UUID) -> bool:
        with self._database.session() as session:
            record = session.get(EntityRecord, entity_id)
            if record is None:
                return False
            record.deleted_at = datetime.now(UTC)
            logger.debug("Soft-deleted entity %s", entity_id)
            return True
