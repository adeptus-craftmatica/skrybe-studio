from __future__ import annotations

import pytest

from skrybe_studio.core.contracts.entity_type import EntityTypeDefinition
from skrybe_studio.core.entities.type_registry import DuplicateEntityTypeError, EntityTypeRegistry


def _definition(
    type_id: str = "story_bible.character", owner: str = "story_bible"
) -> EntityTypeDefinition:
    return EntityTypeDefinition(
        type_id=type_id,
        display_name="Character",
        plural_display_name="Characters",
        owning_plugin_id=owner,
    )


def test_register_and_get() -> None:
    registry = EntityTypeRegistry()
    definition = _definition()

    registry.register(definition)

    assert registry.get("story_bible.character") is definition


def test_get_unknown_type_returns_none() -> None:
    registry = EntityTypeRegistry()
    assert registry.get("does.not.exist") is None


def test_duplicate_type_id_raises() -> None:
    registry = EntityTypeRegistry()
    registry.register(_definition())

    with pytest.raises(DuplicateEntityTypeError):
        registry.register(_definition())


def test_unregister_removes_the_type() -> None:
    registry = EntityTypeRegistry()
    registry.register(_definition())

    registry.unregister("story_bible.character")

    assert registry.get("story_bible.character") is None


def test_unregister_unknown_type_is_a_no_op() -> None:
    registry = EntityTypeRegistry()
    registry.unregister("does.not.exist")  # must not raise


def test_all_lists_every_registered_type() -> None:
    registry = EntityTypeRegistry()
    registry.register(_definition("story_bible.character"))
    registry.register(_definition("story_bible.location"))

    assert {d.type_id for d in registry.all()} == {"story_bible.character", "story_bible.location"}


def test_by_owner_filters_to_the_owning_plugin() -> None:
    registry = EntityTypeRegistry()
    registry.register(_definition("story_bible.character", owner="story_bible"))
    registry.register(_definition("assets.asset", owner="assets"))

    story_bible_types = registry.by_owner("story_bible")

    assert [d.type_id for d in story_bible_types] == ["story_bible.character"]


def test_defaults_favor_a_calm_default_experience() -> None:
    definition = _definition()

    assert definition.user_instantiable is True
    assert definition.user_extensible is True
    assert definition.user_archivable is True
    assert definition.icon_id is None
    assert definition.capabilities == ()
