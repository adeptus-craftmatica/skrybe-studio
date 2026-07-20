from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from skrybe_studio.plugins.story_bible.domain.enums import FieldType
from skrybe_studio.plugins.story_bible.domain.models import (
    EntityType,
    FieldDefinition,
    StoryBibleEntity,
)
from skrybe_studio.plugins.story_bible.infrastructure.repositories import (
    EntityTypeRepository,
    FieldDefinitionRepository,
    FieldValueRepository,
    StoryBibleEntityRepository,
    sort_order_between,
)


def test_sort_order_between_produces_a_deterministic_midpoint() -> None:
    assert sort_order_between(None, None) > 0
    assert sort_order_between(1.0, 3.0) == 2.0
    assert sort_order_between(None, 5.0) < 5.0
    assert sort_order_between(5.0, None) > 5.0


def _entity_type(type_key: str = "spaceship") -> EntityType:
    now = datetime.now(UTC)
    return EntityType(
        id=uuid4(),
        type_key=type_key,
        is_builtin=False,
        display_name="Spaceship",
        plural_display_name="Spaceships",
        created_at=now,
        updated_at=now,
    )


def test_add_and_get_entity_type(entity_type_repository: EntityTypeRepository) -> None:
    entity_type = _entity_type()
    entity_type_repository.add(entity_type)

    fetched = entity_type_repository.get(entity_type.id)

    assert fetched is not None
    assert fetched.type_key == "spaceship"
    assert fetched.entity_type_id == "story_bible.spaceship"


def test_get_by_key_finds_the_type(entity_type_repository: EntityTypeRepository) -> None:
    entity_type = _entity_type()
    entity_type_repository.add(entity_type)

    assert entity_type_repository.get_by_key("spaceship") is not None
    assert entity_type_repository.get_by_key("does-not-exist") is None


def test_list_excludes_archived_by_default(entity_type_repository: EntityTypeRepository) -> None:
    entity_type = _entity_type()
    entity_type_repository.add(entity_type)
    entity_type_repository.set_archived(entity_type.id, datetime.now(UTC))

    assert entity_type_repository.list() == []
    assert len(entity_type_repository.list(include_archived=True)) == 1


def test_field_definition_requires_a_real_entity_type(
    entity_type_repository: EntityTypeRepository,
    field_definition_repository: FieldDefinitionRepository,
) -> None:
    entity_type = _entity_type()
    entity_type_repository.add(entity_type)
    now = datetime.now(UTC)

    field_definition_repository.add(
        FieldDefinition(
            id=uuid4(),
            entity_type_id=entity_type.id,
            internal_key="hull_class",
            display_label="Hull Class",
            field_type=FieldType.SHORT_TEXT,
            sort_order=1.0,
            created_at=now,
            updated_at=now,
        )
    )

    fields = field_definition_repository.list_for_type(entity_type.id)
    assert [f.internal_key for f in fields] == ["hull_class"]


def test_field_definitions_are_ordered_by_sort_order(
    entity_type_repository: EntityTypeRepository,
    field_definition_repository: FieldDefinitionRepository,
) -> None:
    entity_type = _entity_type()
    entity_type_repository.add(entity_type)
    now = datetime.now(UTC)
    second = FieldDefinition(
        id=uuid4(),
        entity_type_id=entity_type.id,
        internal_key="b",
        display_label="B",
        field_type=FieldType.SHORT_TEXT,
        sort_order=2.0,
        created_at=now,
        updated_at=now,
    )
    first = FieldDefinition(
        id=uuid4(),
        entity_type_id=entity_type.id,
        internal_key="a",
        display_label="A",
        field_type=FieldType.SHORT_TEXT,
        sort_order=1.0,
        created_at=now,
        updated_at=now,
    )
    field_definition_repository.add(second)
    field_definition_repository.add(first)

    ordered = field_definition_repository.list_for_type(entity_type.id)

    assert [f.internal_key for f in ordered] == ["a", "b"]


def test_inactive_fields_excluded_by_default(
    entity_type_repository: EntityTypeRepository,
    field_definition_repository: FieldDefinitionRepository,
) -> None:
    entity_type = _entity_type()
    entity_type_repository.add(entity_type)
    now = datetime.now(UTC)
    field = FieldDefinition(
        id=uuid4(),
        entity_type_id=entity_type.id,
        internal_key="a",
        display_label="A",
        field_type=FieldType.SHORT_TEXT,
        sort_order=1.0,
        created_at=now,
        updated_at=now,
    )
    field_definition_repository.add(field)

    field_definition_repository.update(field.id, active=False)

    assert field_definition_repository.list_for_type(entity_type.id) == []
    assert (
        len(field_definition_repository.list_for_type(entity_type.id, include_inactive=True)) == 1
    )


def test_entity_requires_a_real_entity_type(
    entity_type_repository: EntityTypeRepository,
    story_bible_entity_repository: StoryBibleEntityRepository,
) -> None:
    entity_type = _entity_type()
    entity_type_repository.add(entity_type)
    now = datetime.now(UTC)

    entity = StoryBibleEntity(
        id=uuid4(),
        entity_type_id=entity_type.id,
        primary_name="The Nautilus",
        created_at=now,
        updated_at=now,
    )
    story_bible_entity_repository.add(entity)

    fetched = story_bible_entity_repository.get(entity.id)
    assert fetched is not None
    assert fetched.primary_name == "The Nautilus"


def test_field_value_upsert(
    entity_type_repository: EntityTypeRepository,
    story_bible_entity_repository: StoryBibleEntityRepository,
    field_definition_repository: FieldDefinitionRepository,
    field_value_repository: FieldValueRepository,
) -> None:
    entity_type = _entity_type()
    entity_type_repository.add(entity_type)
    now = datetime.now(UTC)
    entity = StoryBibleEntity(
        id=uuid4(),
        entity_type_id=entity_type.id,
        primary_name="The Nautilus",
        created_at=now,
        updated_at=now,
    )
    story_bible_entity_repository.add(entity)
    field = FieldDefinition(
        id=uuid4(),
        entity_type_id=entity_type.id,
        internal_key="hull_class",
        display_label="Hull Class",
        field_type=FieldType.SHORT_TEXT,
        sort_order=1.0,
        created_at=now,
        updated_at=now,
    )
    field_definition_repository.add(field)

    field_value_repository.set(entity.id, field.id, "Cruiser")
    field_value_repository.set(entity.id, field.id, "Frigate")  # upsert, not a second row

    values = field_value_repository.get_for_entity(entity.id)
    assert values == {field.id: "Frigate"}
