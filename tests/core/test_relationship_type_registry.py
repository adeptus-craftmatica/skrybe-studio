from __future__ import annotations

import pytest

from skrybe_studio.core.contracts.relationship_type import RelationshipTypeDefinition
from skrybe_studio.core.entities.relationship_type_registry import (
    DuplicateRelationshipTypeError,
    RelationshipTypeRegistry,
)


def _definition(
    type_id: str = "story_bible.parent_of", owner: str = "story_bible"
) -> RelationshipTypeDefinition:
    return RelationshipTypeDefinition(
        type_id=type_id,
        display_label="Parent of",
        reverse_label="Child of",
        owning_plugin_id=owner,
    )


def test_register_and_get() -> None:
    registry = RelationshipTypeRegistry()
    definition = _definition()

    registry.register(definition)

    assert registry.get("story_bible.parent_of") is definition


def test_get_unknown_type_returns_none() -> None:
    registry = RelationshipTypeRegistry()
    assert registry.get("does.not.exist") is None


def test_duplicate_type_id_raises() -> None:
    registry = RelationshipTypeRegistry()
    registry.register(_definition())

    with pytest.raises(DuplicateRelationshipTypeError):
        registry.register(_definition())


def test_unregister_removes_the_type() -> None:
    registry = RelationshipTypeRegistry()
    registry.register(_definition())

    registry.unregister("story_bible.parent_of")

    assert registry.get("story_bible.parent_of") is None


def test_all_lists_every_registered_type() -> None:
    registry = RelationshipTypeRegistry()
    registry.register(_definition("story_bible.parent_of"))
    registry.register(_definition("story_bible.knows"))

    assert {d.type_id for d in registry.all()} == {"story_bible.parent_of", "story_bible.knows"}


def test_by_owner_filters_to_the_owning_plugin() -> None:
    registry = RelationshipTypeRegistry()
    registry.register(_definition("story_bible.parent_of", owner="story_bible"))
    registry.register(_definition("manuscript.cover_asset", owner="manuscript"))

    manuscript_types = registry.by_owner("manuscript")

    assert [d.type_id for d in manuscript_types] == ["manuscript.cover_asset"]


def test_defaults_are_directed_many_to_many_and_unrestricted() -> None:
    definition = _definition()

    assert definition.directed is True
    assert definition.cardinality == "many_to_many"
    assert definition.allowed_source_types == ()
    assert definition.allowed_target_types == ()
    assert definition.user_editable is True
