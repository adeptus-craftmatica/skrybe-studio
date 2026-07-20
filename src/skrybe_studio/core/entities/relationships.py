"""CRUD service for the shared `Relationship` contract."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, select

from skrybe_studio.core.contracts.relationship import Relationship
from skrybe_studio.core.storage.database import Database
from skrybe_studio.core.storage.models import RelationshipRecord

logger = logging.getLogger(__name__)


def _to_relationship(record: RelationshipRecord) -> Relationship:
    return Relationship(
        id=record.id,
        source_entity_id=record.source_entity_id,
        target_entity_id=record.target_entity_id,
        relationship_type=record.relationship_type,
        plugin_owner=record.plugin_owner,
        created_at=record.created_at,
        updated_at=record.updated_at,
        metadata=dict(record.metadata_json or {}),
    )


class RelationshipService:
    """Creates and queries typed connections between entities."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def create(
        self,
        *,
        source_entity_id: UUID,
        target_entity_id: UUID,
        relationship_type: str,
        plugin_owner: str,
        metadata: dict[str, Any] | None = None,
    ) -> Relationship:
        now = datetime.now(UTC)
        relationship = Relationship(
            id=uuid4(),
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            plugin_owner=plugin_owner,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        with self._database.session() as session:
            session.add(
                RelationshipRecord(
                    id=relationship.id,
                    source_entity_id=relationship.source_entity_id,
                    target_entity_id=relationship.target_entity_id,
                    relationship_type=relationship.relationship_type,
                    plugin_owner=relationship.plugin_owner,
                    created_at=relationship.created_at,
                    updated_at=relationship.updated_at,
                    metadata_json=dict(relationship.metadata),
                )
            )
        logger.debug(
            "Created relationship %s (%s -> %s)",
            relationship.relationship_type,
            source_entity_id,
            target_entity_id,
        )
        return relationship

    def for_entity(self, entity_id: UUID) -> list[Relationship]:
        with self._database.session() as session:
            stmt = select(RelationshipRecord).where(
                or_(
                    RelationshipRecord.source_entity_id == entity_id,
                    RelationshipRecord.target_entity_id == entity_id,
                )
            )
            return [_to_relationship(record) for record in session.scalars(stmt)]

    def delete(self, relationship_id: UUID) -> bool:
        with self._database.session() as session:
            record = session.get(RelationshipRecord, relationship_id)
            if record is None:
                return False
            session.delete(record)
            return True
