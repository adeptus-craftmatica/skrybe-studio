"""Registers relationship-type definitions so any plugin can look up display
metadata (labels, directionality, allowed endpoint types) for a relationship
type it doesn't own. Same rationale and shape as `EntityTypeRegistry`;
project-scoped for the same reason (project-local custom relationship
types are project data).
"""

from __future__ import annotations

import logging

from skrybe_studio.core.contracts.relationship_type import RelationshipTypeDefinition

logger = logging.getLogger(__name__)


class DuplicateRelationshipTypeError(RuntimeError):
    """Raised when two relationship types are registered under the same type_id."""


class RelationshipTypeRegistry:
    def __init__(self) -> None:
        self._types: dict[str, RelationshipTypeDefinition] = {}

    def register(self, definition: RelationshipTypeDefinition) -> None:
        if definition.type_id in self._types:
            raise DuplicateRelationshipTypeError(
                f"Relationship type '{definition.type_id}' is already registered"
            )
        self._types[definition.type_id] = definition
        logger.debug("Registered relationship type '%s'", definition.type_id)

    def unregister(self, type_id: str) -> None:
        self._types.pop(type_id, None)

    def get(self, type_id: str) -> RelationshipTypeDefinition | None:
        return self._types.get(type_id)

    def all(self) -> list[RelationshipTypeDefinition]:
        return list(self._types.values())

    def by_owner(self, plugin_id: str) -> list[RelationshipTypeDefinition]:
        return [d for d in self._types.values() if d.owning_plugin_id == plugin_id]
