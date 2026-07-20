"""Manages entity-type definitions and their field definitions.

Keeps the core `EntityTypeRegistry` (project-scoped, shared with every
other plugin) in sync with this plugin's own project-local storage:
whenever a type is created, renamed, or archived here, the same change is
reflected into `context.entity_types` so other plugins can look up display
metadata without importing this one.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from skrybe_studio.core.contracts.entity_type import EntityTypeDefinition
from skrybe_studio.core.entities.type_registry import EntityTypeRegistry
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.story_bible.domain.builtins import ALL_BUILTIN_TYPES, BuiltinTypeSpec
from skrybe_studio.plugins.story_bible.domain.enums import FieldType
from skrybe_studio.plugins.story_bible.domain.exceptions import (
    DuplicateFieldKeyError,
    DuplicateTypeKeyError,
    EntityTypeNotFoundError,
)
from skrybe_studio.plugins.story_bible.domain.models import (
    PLUGIN_ID,
    EntityType,
    FieldDefinition,
    entity_type_id_for,
)
from skrybe_studio.plugins.story_bible.infrastructure.repositories import (
    EntityTypeRepository,
    FieldDefinitionRepository,
    sort_order_between,
)

_TYPE_KEY_PATTERN = re.compile(r"[^a-z0-9_]+")


def slugify_type_key(display_name: str) -> str:
    """A machine-safe internal key derived from a display name, e.g.
    "Political Faction" -> "political_faction". Not guaranteed unique on
    its own - `SchemaService.create_custom_type` still checks for
    collisions and raises `DuplicateTypeKeyError`.
    """
    lowered = display_name.strip().lower().replace(" ", "_").replace("-", "_")
    return _TYPE_KEY_PATTERN.sub("", lowered) or "custom_type"


class SchemaService:
    def __init__(
        self,
        types: EntityTypeRepository,
        fields: FieldDefinitionRepository,
        registry: EntityTypeRegistry,
        events: EventBus,
    ) -> None:
        self._types = types
        self._fields = fields
        self._registry = registry
        self._events = events

    # --- built-in seeding ------------------------------------------------------------

    def seed_builtins_if_needed(self) -> None:
        """Idempotent: seeds every built-in type + its default fields once
        per project, on first activation. Safe to call on every activate()
        after that - it only inserts types that don't already exist by key.
        """
        for spec in ALL_BUILTIN_TYPES:
            if self._types.get_by_key(spec.type_key) is None:
                self._seed_builtin_type(spec)

    def _seed_builtin_type(self, spec: BuiltinTypeSpec) -> None:
        now = datetime.now(UTC)
        entity_type = EntityType(
            id=uuid4(),
            type_key=spec.type_key,
            is_builtin=True,
            display_name=spec.display_name,
            plural_display_name=spec.plural_display_name,
            description=spec.description,
            icon_id=spec.icon_id,
            created_at=now,
            updated_at=now,
        )
        self._types.add(entity_type)
        sort_order = None
        for field_spec in spec.fields:
            sort_order = sort_order_between(sort_order, None)
            self._fields.add(
                FieldDefinition(
                    id=uuid4(),
                    entity_type_id=entity_type.id,
                    internal_key=field_spec.internal_key,
                    display_label=field_spec.display_label,
                    field_type=field_spec.field_type,
                    sort_order=sort_order,
                    required=field_spec.required,
                    section=field_spec.section,
                    searchable=field_spec.searchable,
                    display_in_list=field_spec.display_in_list,
                    display_in_card=field_spec.display_in_card,
                    created_at=now,
                    updated_at=now,
                )
            )

    def register_all_into_core(self) -> None:
        """Registers every non-archived type (built-in + custom) from this
        project into the shared `EntityTypeRegistry` - called once per
        `activate()`, after seeding, so the registry always reflects the
        currently open project.
        """
        for entity_type in self._types.list():
            self._register_one(entity_type)

    def _register_one(self, entity_type: EntityType) -> None:
        # Registers or re-registers (rename/restore call this on an
        # already-registered type) - EntityTypeRegistry.register() guards
        # against a genuine cross-plugin ID collision, not against this
        # plugin refreshing its own entry, so unregister first to make this
        # an upsert.
        self._registry.unregister(entity_type.entity_type_id)
        self._registry.register(
            EntityTypeDefinition(
                type_id=entity_type.entity_type_id,
                display_name=entity_type.display_name,
                plural_display_name=entity_type.plural_display_name,
                owning_plugin_id=PLUGIN_ID,
                icon_id=entity_type.icon_id,
                color_token=entity_type.color_token,
                description=entity_type.description,
                user_instantiable=entity_type.user_instantiable,
                user_extensible=entity_type.user_extensible,
                user_archivable=entity_type.user_archivable,
            )
        )

    def unregister_all_from_core(self) -> None:
        """Called from `deactivate()` - the registry is project-scoped
        (a fresh instance per open project), but unregistering explicitly
        means a plugin that inspects it mid-deactivation never sees stale
        entries."""
        for entity_type in self._types.list(include_archived=True):
            self._registry.unregister(entity_type.entity_type_id)

    # --- custom types ------------------------------------------------------------------

    def create_custom_type(
        self,
        display_name: str,
        plural_display_name: str,
        *,
        type_key: str | None = None,
        description: str = "",
        icon_id: str | None = None,
        color_token: str | None = None,
    ) -> EntityType:
        key = type_key or slugify_type_key(display_name)
        if self._types.get_by_key(key) is not None:
            raise DuplicateTypeKeyError(f"An entity type with key '{key}' already exists")
        now = datetime.now(UTC)
        entity_type = EntityType(
            id=uuid4(),
            type_key=key,
            is_builtin=False,
            display_name=display_name,
            plural_display_name=plural_display_name,
            description=description,
            icon_id=icon_id,
            color_token=color_token,
            created_at=now,
            updated_at=now,
        )
        self._types.add(entity_type)
        self._register_one(entity_type)
        return entity_type

    def rename_type(
        self,
        type_id: UUID,
        *,
        display_name: str | None = None,
        plural_display_name: str | None = None,
        description: str | None = None,
        icon_id: str | None = None,
        color_token: str | None = None,
    ) -> EntityType | None:
        updated = self._types.update(
            type_id,
            display_name=display_name,
            plural_display_name=plural_display_name,
            description=description,
            icon_id=icon_id,
            color_token=color_token,
        )
        if updated is not None:
            self._register_one(updated)
        return updated

    def archive_type(self, type_id: UUID) -> None:
        self._types.set_archived(type_id, datetime.now(UTC))
        entity_type = self._types.get(type_id)
        if entity_type is not None:
            self._registry.unregister(entity_type.entity_type_id)

    def restore_type(self, type_id: UUID) -> None:
        self._types.set_archived(type_id, None)
        entity_type = self._types.get(type_id)
        if entity_type is not None:
            self._register_one(entity_type)

    def get_type(self, type_id: UUID) -> EntityType | None:
        return self._types.get(type_id)

    def get_type_by_key(self, type_key: str) -> EntityType | None:
        return self._types.get_by_key(type_key)

    def list_types(self, *, include_archived: bool = False) -> list[EntityType]:
        return self._types.list(include_archived=include_archived)

    # --- fields ------------------------------------------------------------------------

    def add_field(
        self,
        entity_type_id: UUID,
        internal_key: str,
        display_label: str,
        field_type: FieldType,
        **kwargs: object,
    ) -> FieldDefinition:
        if self._types.get(entity_type_id) is None:
            raise EntityTypeNotFoundError(f"No entity type with id {entity_type_id}")
        existing = self._fields.list_for_type(entity_type_id, include_inactive=True)
        if any(f.internal_key == internal_key for f in existing):
            raise DuplicateFieldKeyError(
                f"Field '{internal_key}' already exists on this entity type"
            )
        now = datetime.now(UTC)
        sort_order = sort_order_between(self._fields.last_sort_order(entity_type_id), None)
        definition = FieldDefinition(
            id=uuid4(),
            entity_type_id=entity_type_id,
            internal_key=internal_key,
            display_label=display_label,
            field_type=field_type,
            sort_order=sort_order,
            created_at=now,
            updated_at=now,
            **kwargs,  # type: ignore[arg-type]
        )
        self._fields.add(definition)
        return definition

    def update_field(self, field_id: UUID, **kwargs: object) -> FieldDefinition | None:
        return self._fields.update(field_id, **kwargs)  # type: ignore[arg-type]

    def deactivate_field(self, field_id: UUID) -> None:
        self._fields.update(field_id, active=False)

    def reactivate_field(self, field_id: UUID) -> None:
        self._fields.update(field_id, active=True)

    def list_fields(
        self, entity_type_id: UUID, *, include_inactive: bool = False
    ) -> list[FieldDefinition]:
        return self._fields.list_for_type(entity_type_id, include_inactive=include_inactive)

    def get_field(self, field_id: UUID) -> FieldDefinition | None:
        return self._fields.get(field_id)

    def reorder_field(self, field_id: UUID, *, direction: int) -> None:
        """Moves a field up (`direction=-1`) or down (`direction=1`) among
        its active siblings on the same entity type - a single-row sort_order
        update, never a bulk renumbering of every field. Mirrors
        `HierarchyService.move_sibling`'s swap-then-recompute-neighbors
        approach exactly.
        """
        field_definition = self._fields.get(field_id)
        if field_definition is None:
            return
        siblings = self.list_fields(field_definition.entity_type_id)
        index = next((i for i, f in enumerate(siblings) if f.id == field_id), None)
        if index is None:
            return
        target_index = index + direction
        if not (0 <= target_index < len(siblings)):
            return
        siblings[index], siblings[target_index] = siblings[target_index], siblings[index]
        before = siblings[target_index - 1].sort_order if target_index > 0 else None
        after = siblings[target_index + 1].sort_order if target_index + 1 < len(siblings) else None
        self._fields.set_sort_order(field_id, sort_order_between(before, after))


__all__ = ["SchemaService", "entity_type_id_for", "slugify_type_key"]
