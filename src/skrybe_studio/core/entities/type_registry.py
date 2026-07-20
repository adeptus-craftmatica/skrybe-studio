"""Registers entity-type definitions so any plugin can look up display
metadata (name, icon, plural) for an entity type it doesn't own - without
importing the owning plugin. Mirrors `PanelRegistry`'s "ID to metadata"
shape.

Project-scoped: constructed fresh per open project (see
`ProjectService._open_paths`) because project-local custom entity types are
project data, not application code - a different project can have a
different set of custom types. Built-in types are re-registered by their
owning plugin's `activate()` every time a project opens (cheap, since
they're just dataclass instances), alongside the project's custom types.
"""

from __future__ import annotations

import logging

from skrybe_studio.core.contracts.entity_type import EntityTypeDefinition

logger = logging.getLogger(__name__)


class DuplicateEntityTypeError(RuntimeError):
    """Raised when two entity types are registered under the same type_id."""


class EntityTypeRegistry:
    def __init__(self) -> None:
        self._types: dict[str, EntityTypeDefinition] = {}

    def register(self, definition: EntityTypeDefinition) -> None:
        if definition.type_id in self._types:
            raise DuplicateEntityTypeError(
                f"Entity type '{definition.type_id}' is already registered"
            )
        self._types[definition.type_id] = definition
        logger.debug("Registered entity type '%s'", definition.type_id)

    def unregister(self, type_id: str) -> None:
        self._types.pop(type_id, None)

    def get(self, type_id: str) -> EntityTypeDefinition | None:
        return self._types.get(type_id)

    def all(self) -> list[EntityTypeDefinition]:
        return list(self._types.values())

    def by_owner(self, plugin_id: str) -> list[EntityTypeDefinition]:
        return [d for d in self._types.values() if d.owning_plugin_id == plugin_id]
