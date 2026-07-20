from __future__ import annotations

import pytest

from skrybe_studio.core.entities.type_registry import EntityTypeRegistry
from skrybe_studio.plugins.story_bible.application.schema_service import SchemaService
from skrybe_studio.plugins.story_bible.domain.enums import FieldType
from skrybe_studio.plugins.story_bible.domain.exceptions import (
    DuplicateFieldKeyError,
    DuplicateTypeKeyError,
)


def test_seed_builtins_registers_every_built_in_type(schema: SchemaService) -> None:
    schema.seed_builtins_if_needed()

    keys = {t.type_key for t in schema.list_types()}
    assert {"character", "location", "organization", "item", "culture"} <= keys


def test_seed_builtins_is_idempotent(schema: SchemaService) -> None:
    schema.seed_builtins_if_needed()
    schema.seed_builtins_if_needed()

    keys = [t.type_key for t in schema.list_types()]
    assert keys.count("character") == 1


def test_seed_builtins_creates_default_fields(schema: SchemaService) -> None:
    schema.seed_builtins_if_needed()
    character = schema.get_type_by_key("character")
    assert character is not None

    fields = schema.list_fields(character.id)

    assert any(f.internal_key == "full_name" for f in fields)
    assert any(f.internal_key == "portrait_asset" for f in fields)


def test_register_all_into_core_populates_the_registry(
    schema: SchemaService, entity_type_registry: EntityTypeRegistry
) -> None:
    schema.seed_builtins_if_needed()

    schema.register_all_into_core()

    assert entity_type_registry.get("story_bible.character") is not None


def test_unregister_all_from_core_clears_the_registry(
    schema: SchemaService, entity_type_registry: EntityTypeRegistry
) -> None:
    schema.seed_builtins_if_needed()
    schema.register_all_into_core()

    schema.unregister_all_from_core()

    assert entity_type_registry.get("story_bible.character") is None


def test_create_custom_type_registers_into_core(
    schema: SchemaService, entity_type_registry: EntityTypeRegistry
) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")

    assert entity_type.type_key == "spaceship"
    assert entity_type_registry.get("story_bible.spaceship") is not None


def test_create_custom_type_with_duplicate_key_raises(schema: SchemaService) -> None:
    schema.create_custom_type("Spaceship", "Spaceships")

    with pytest.raises(DuplicateTypeKeyError):
        schema.create_custom_type("Space Ship", "Space Ships", type_key="spaceship")


def test_rename_type_updates_the_core_registry(
    schema: SchemaService, entity_type_registry: EntityTypeRegistry
) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")

    schema.rename_type(entity_type.id, display_name="Starship")

    registered = entity_type_registry.get("story_bible.spaceship")
    assert registered is not None
    assert registered.display_name == "Starship"


def test_archive_type_removes_it_from_core_registry_but_keeps_the_row(
    schema: SchemaService, entity_type_registry: EntityTypeRegistry
) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")

    schema.archive_type(entity_type.id)

    assert entity_type_registry.get("story_bible.spaceship") is None
    archived_type = schema.get_type(entity_type.id)
    assert archived_type is not None
    assert archived_type.is_archived is True
    assert entity_type.id not in {t.id for t in schema.list_types()}


def test_restore_type_re_registers_it(
    schema: SchemaService, entity_type_registry: EntityTypeRegistry
) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    schema.archive_type(entity_type.id)

    schema.restore_type(entity_type.id)

    assert entity_type_registry.get("story_bible.spaceship") is not None
    restored_type = schema.get_type(entity_type.id)
    assert restored_type is not None
    assert restored_type.is_archived is False


def test_add_field_assigns_increasing_sort_order(schema: SchemaService) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")

    first = schema.add_field(entity_type.id, "name", "Name", FieldType.SHORT_TEXT)
    second = schema.add_field(entity_type.id, "class", "Class", FieldType.SHORT_TEXT)

    assert first.sort_order < second.sort_order
    assert [f.internal_key for f in schema.list_fields(entity_type.id)] == ["name", "class"]


def test_add_field_with_duplicate_key_raises(schema: SchemaService) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    schema.add_field(entity_type.id, "name", "Name", FieldType.SHORT_TEXT)

    with pytest.raises(DuplicateFieldKeyError):
        schema.add_field(entity_type.id, "name", "Name Again", FieldType.SHORT_TEXT)


def test_deactivate_field_hides_it_from_the_default_listing(schema: SchemaService) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    field = schema.add_field(entity_type.id, "name", "Name", FieldType.SHORT_TEXT)

    schema.deactivate_field(field.id)

    assert schema.list_fields(entity_type.id) == []
    assert len(schema.list_fields(entity_type.id, include_inactive=True)) == 1


def test_reactivate_field_round_trip(schema: SchemaService) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    field = schema.add_field(entity_type.id, "name", "Name", FieldType.SHORT_TEXT)
    schema.deactivate_field(field.id)

    schema.reactivate_field(field.id)

    assert [f.internal_key for f in schema.list_fields(entity_type.id)] == ["name"]


def test_reorder_field_moves_it_up(schema: SchemaService) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    first = schema.add_field(entity_type.id, "a", "A", FieldType.SHORT_TEXT)
    schema.add_field(entity_type.id, "b", "B", FieldType.SHORT_TEXT)

    schema.reorder_field(first.id, direction=1)

    assert [f.internal_key for f in schema.list_fields(entity_type.id)] == ["b", "a"]


def test_reorder_field_past_the_end_is_a_no_op(schema: SchemaService) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    first = schema.add_field(entity_type.id, "a", "A", FieldType.SHORT_TEXT)

    schema.reorder_field(first.id, direction=1)

    assert [f.internal_key for f in schema.list_fields(entity_type.id)] == ["a"]


def test_update_field_changes_metadata_without_touching_others(schema: SchemaService) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    field = schema.add_field(entity_type.id, "name", "Name", FieldType.SHORT_TEXT)

    updated = schema.update_field(field.id, display_label="Ship Name", required=True)

    assert updated is not None
    assert updated.display_label == "Ship Name"
    assert updated.required is True
    assert updated.internal_key == "name"
