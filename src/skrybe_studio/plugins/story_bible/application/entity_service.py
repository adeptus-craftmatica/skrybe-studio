"""Manages Story Bible entities and their field values.

**Authoritative title**: `primary_name` is authoritative (see
`domain/models.py`); every method that changes it also calls
`EntityService.rename()` so the shared entity title never drifts out of
sync. Archiving/restoring here is entirely plugin-local and reversible -
it never touches the shared `Entity`'s soft deletion. "Delete permanently"
is deliberately not exposed by this service in 0.3, matching "delete
permanently only through a clearly destructive workflow" by simply not
offering one yet rather than building an under-designed one.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from skrybe_studio.core.entities.service import EntityService
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.story_bible.application.events import (
    EntityArchived,
    EntityCreated,
    EntityMetadataChanged,
    EntityRenamed,
    EntityRestored,
    FieldValueChanged,
)
from skrybe_studio.plugins.story_bible.application.schema_service import SchemaService
from skrybe_studio.plugins.story_bible.domain.exceptions import EntityTypeNotFoundError
from skrybe_studio.plugins.story_bible.domain.models import PLUGIN_ID, StoryBibleEntity
from skrybe_studio.plugins.story_bible.domain.validation import validate_value
from skrybe_studio.plugins.story_bible.infrastructure.repositories import (
    FieldValueRepository,
    StoryBibleEntityRepository,
)


class StoryBibleEntityService:
    def __init__(
        self,
        entities_repo: StoryBibleEntityRepository,
        field_values: FieldValueRepository,
        schema: SchemaService,
        entities: EntityService,
        events: EventBus,
    ) -> None:
        self._entities_repo = entities_repo
        self._field_values = field_values
        self._schema = schema
        self._entities = entities
        self._events = events

    def create_entity(
        self,
        entity_type_id: UUID,
        primary_name: str,
        *,
        summary: str = "",
        template_field_values: dict[str, object] | None = None,
    ) -> StoryBibleEntity:
        entity_type = self._schema.get_type(entity_type_id)
        if entity_type is None:
            raise EntityTypeNotFoundError(f"No entity type with id {entity_type_id}")

        now = datetime.now(UTC)
        entity = StoryBibleEntity(
            id=uuid4(),
            entity_type_id=entity_type_id,
            primary_name=primary_name,
            summary=summary,
            created_at=now,
            updated_at=now,
        )
        self._entities_repo.add(entity)
        self._entities.create(
            entity_type=entity_type.entity_type_id,
            title=primary_name,
            plugin_owner=PLUGIN_ID,
            entity_id=entity.id,
        )

        if template_field_values:
            fields_by_key = {f.internal_key: f for f in self._schema.list_fields(entity_type_id)}
            for internal_key, value in template_field_values.items():
                field_definition = fields_by_key.get(internal_key)
                if field_definition is not None:
                    self._field_values.set(entity.id, field_definition.id, value)

        self._events.publish(
            EntityCreated(
                entity_id=entity.id, entity_type_id=entity_type_id, primary_name=primary_name
            )
        )
        return entity

    def rename_entity(self, entity_id: UUID, primary_name: str) -> StoryBibleEntity | None:
        updated = self._entities_repo.update(entity_id, primary_name=primary_name)
        if updated is not None:
            self._entities.rename(entity_id, primary_name)
            self._events.publish(EntityRenamed(entity_id=entity_id, primary_name=primary_name))
        return updated

    def update_metadata(
        self,
        entity_id: UUID,
        *,
        summary: str | None = None,
        aliases: tuple[str, ...] | None = None,
        notes: str | None = None,
        status: str | None = None,
        tags: tuple[str, ...] | None = None,
    ) -> StoryBibleEntity | None:
        updated = self._entities_repo.update(
            entity_id, summary=summary, aliases=aliases, notes=notes, status=status, tags=tags
        )
        if updated is not None:
            self._events.publish(EntityMetadataChanged(entity_id=entity_id))
        return updated

    def change_entity_type(
        self, entity_id: UUID, new_entity_type_id: UUID
    ) -> StoryBibleEntity | None:
        """Field values keyed to the old type's field definitions are left
        in place (not deleted) - they simply stop being shown once the
        entity's `entity_type_id` no longer matches them, preserving data
        rather than migrating or discarding it.
        """
        if self._schema.get_type(new_entity_type_id) is None:
            raise EntityTypeNotFoundError(f"No entity type with id {new_entity_type_id}")
        updated = self._entities_repo.set_entity_type(entity_id, new_entity_type_id)
        if updated is not None:
            self._events.publish(EntityMetadataChanged(entity_id=entity_id))
        return updated

    def duplicate_entity(self, entity_id: UUID) -> StoryBibleEntity | None:
        original = self._entities_repo.get(entity_id)
        if original is None:
            return None
        duplicate = self.create_entity(
            original.entity_type_id, f"{original.primary_name} Copy", summary=original.summary
        )
        self.update_metadata(
            duplicate.id, aliases=original.aliases, notes=original.notes, tags=original.tags
        )
        for field_id, value in self._field_values.get_for_entity(entity_id).items():
            self._field_values.set(duplicate.id, field_id, value)
        return self._entities_repo.get(duplicate.id)

    def archive_entity(self, entity_id: UUID) -> bool:
        entity = self._entities_repo.get(entity_id)
        if entity is None:
            return False
        self._entities_repo.set_archived(entity_id, datetime.now(UTC))
        self._events.publish(EntityArchived(entity_id=entity_id))
        return True

    def restore_entity(self, entity_id: UUID) -> bool:
        entity = self._entities_repo.get(entity_id)
        if entity is None:
            return False
        self._entities_repo.set_archived(entity_id, None)
        self._events.publish(EntityRestored(entity_id=entity_id))
        return True

    def get_entity(self, entity_id: UUID) -> StoryBibleEntity | None:
        return self._entities_repo.get(entity_id)

    def list_entities(
        self, entity_type_id: UUID | None = None, *, include_archived: bool = False
    ) -> list[StoryBibleEntity]:
        return self._entities_repo.list(
            entity_type_id=entity_type_id, include_archived=include_archived
        )

    def search(self, query: str) -> list[StoryBibleEntity]:
        return self._entities_repo.search(query)

    # --- field values ------------------------------------------------------------------

    def get_field_values(self, entity_id: UUID) -> dict[UUID, object | None]:
        return self._field_values.get_for_entity(entity_id)

    def set_field_value(
        self, entity_id: UUID, field_definition_id: UUID, value: object | None
    ) -> None:
        """A dangling `ENTITY_REFERENCE`/`ASSET_REFERENCE` value (pointing at
        something archived, deleted, or belonging to a disabled plugin) is
        preserved, not rejected - existence is a UI display concern ("show
        unavailable"), not a write-time validation rule, so a plugin being
        temporarily disabled can never silently destroy a stored reference.
        """
        definition = self._schema.get_field(field_definition_id)
        if definition is None:
            raise EntityTypeNotFoundError(f"No field definition with id {field_definition_id}")
        validate_value(definition, value)
        self._field_values.set(entity_id, field_definition_id, value)
        self._events.publish(FieldValueChanged(entity_id=entity_id, field_id=field_definition_id))
