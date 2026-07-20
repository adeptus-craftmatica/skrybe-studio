from __future__ import annotations

from uuid import uuid4

import pytest

from skrybe_studio.core.entities.service import EntityService
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.story_bible.application.entity_service import StoryBibleEntityService
from skrybe_studio.plugins.story_bible.application.events import (
    EntityArchived,
    EntityCreated,
    EntityRenamed,
    FieldValueChanged,
)
from skrybe_studio.plugins.story_bible.application.schema_service import SchemaService
from skrybe_studio.plugins.story_bible.domain.enums import FieldType
from skrybe_studio.plugins.story_bible.domain.exceptions import (
    EntityTypeNotFoundError,
    FieldValidationError,
)


def test_create_entity_publishes_event_and_registers_shared_entity(
    schema: SchemaService,
    story_bible_entities: StoryBibleEntityService,
    entities: EntityService,
    events: EventBus,
) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    received: list[str] = []
    events.subscribe(EntityCreated, lambda event: received.append(event.primary_name))

    ship = story_bible_entities.create_entity(entity_type.id, "The Nautilus")

    assert received == ["The Nautilus"]
    entity = entities.get(ship.id)
    assert entity is not None
    assert entity.entity_type == "story_bible.spaceship"
    assert entity.title == "The Nautilus"


def test_create_entity_with_unknown_type_raises(
    story_bible_entities: StoryBibleEntityService,
) -> None:
    with pytest.raises(EntityTypeNotFoundError):
        story_bible_entities.create_entity(uuid4(), "Nobody")


def test_rename_entity_keeps_shared_entity_title_in_sync(
    schema: SchemaService,
    story_bible_entities: StoryBibleEntityService,
    entities: EntityService,
    events: EventBus,
) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    ship = story_bible_entities.create_entity(entity_type.id, "Old Name")
    received: list[str] = []
    events.subscribe(EntityRenamed, lambda event: received.append(event.primary_name))

    story_bible_entities.rename_entity(ship.id, "New Name")

    entity = entities.get(ship.id)
    assert entity is not None
    assert entity.title == "New Name"
    assert received == ["New Name"]


def test_update_metadata_changes_aliases_tags_and_notes(
    schema: SchemaService, story_bible_entities: StoryBibleEntityService
) -> None:
    entity_type = schema.create_custom_type("Character", "Characters", type_key="custom_character")
    entity = story_bible_entities.create_entity(entity_type.id, "Elena")

    updated = story_bible_entities.update_metadata(
        entity.id, aliases=("El",), tags=("protagonist",), notes="Loves the sea."
    )

    assert updated is not None
    assert updated.aliases == ("El",)
    assert updated.tags == ("protagonist",)
    assert updated.notes == "Loves the sea."


def test_duplicate_entity_copies_metadata_and_field_values(
    schema: SchemaService, story_bible_entities: StoryBibleEntityService
) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    field = schema.add_field(entity_type.id, "class", "Class", FieldType.SHORT_TEXT)
    original = story_bible_entities.create_entity(entity_type.id, "The Nautilus")
    story_bible_entities.update_metadata(original.id, tags=("flagship",))
    story_bible_entities.set_field_value(original.id, field.id, "Cruiser")

    duplicate = story_bible_entities.duplicate_entity(original.id)

    assert duplicate is not None
    assert duplicate.primary_name == "The Nautilus Copy"
    assert duplicate.tags == ("flagship",)
    duplicate_values = story_bible_entities.get_field_values(duplicate.id)
    assert duplicate_values[field.id] == "Cruiser"


def test_archive_and_restore_entity_round_trip(
    schema: SchemaService, story_bible_entities: StoryBibleEntityService, events: EventBus
) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    ship = story_bible_entities.create_entity(entity_type.id, "The Nautilus")
    archived_received: list = []
    events.subscribe(EntityArchived, archived_received.append)

    assert story_bible_entities.archive_entity(ship.id) is True
    archived = story_bible_entities.get_entity(ship.id)
    assert archived is not None
    assert archived.is_archived is True
    assert ship.id not in {e.id for e in story_bible_entities.list_entities(entity_type.id)}
    assert len(archived_received) == 1

    assert story_bible_entities.restore_entity(ship.id) is True
    restored = story_bible_entities.get_entity(ship.id)
    assert restored is not None
    assert restored.is_archived is False


def test_change_entity_type_preserves_orphaned_field_values(
    schema: SchemaService, story_bible_entities: StoryBibleEntityService
) -> None:
    type_a = schema.create_custom_type("TypeA", "TypeAs")
    type_b = schema.create_custom_type("TypeB", "TypeBs")
    field_a = schema.add_field(type_a.id, "only_on_a", "Only On A", FieldType.SHORT_TEXT)
    entity = story_bible_entities.create_entity(type_a.id, "Thing")
    story_bible_entities.set_field_value(entity.id, field_a.id, "some value")

    updated = story_bible_entities.change_entity_type(entity.id, type_b.id)

    assert updated is not None
    assert updated.entity_type_id == type_b.id
    # The old field's value is preserved, not deleted, even though it no
    # longer belongs to the entity's current type.
    assert story_bible_entities.get_field_values(entity.id)[field_a.id] == "some value"


def test_set_field_value_validates_and_publishes_event(
    schema: SchemaService, story_bible_entities: StoryBibleEntityService, events: EventBus
) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    field = schema.add_field(entity_type.id, "hull_integrity", "Hull Integrity", FieldType.INTEGER)
    entity = story_bible_entities.create_entity(entity_type.id, "The Nautilus")
    received: list = []
    events.subscribe(FieldValueChanged, received.append)

    story_bible_entities.set_field_value(entity.id, field.id, 100)

    assert story_bible_entities.get_field_values(entity.id)[field.id] == 100
    assert len(received) == 1

    with pytest.raises(FieldValidationError):
        story_bible_entities.set_field_value(entity.id, field.id, "not a number")


def test_search_matches_primary_name_and_aliases(
    schema: SchemaService, story_bible_entities: StoryBibleEntityService
) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    ship = story_bible_entities.create_entity(entity_type.id, "The Nautilus")
    story_bible_entities.update_metadata(ship.id, aliases=("Silent Runner",))

    by_name = story_bible_entities.search("nautilus")
    by_alias = story_bible_entities.search("silent")

    assert [e.id for e in by_name] == [ship.id]
    assert [e.id for e in by_alias] == [ship.id]
