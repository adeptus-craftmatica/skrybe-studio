from __future__ import annotations

from uuid import uuid4

import pytest

from skrybe_studio.core.navigation.viewer_registry import DuplicateViewerError, EntityViewerRegistry


def test_reveal_invokes_the_handler_for_the_entity_types_namespace() -> None:
    registry = EntityViewerRegistry()
    received: list = []
    registry.register("story_bible", received.append)
    entity_id = uuid4()

    handled = registry.reveal("story_bible.character", entity_id)

    assert handled is True
    assert received == [entity_id]


def test_reveal_with_no_registered_namespace_returns_false() -> None:
    registry = EntityViewerRegistry()

    assert registry.reveal("story_bible.character", uuid4()) is False


def test_has_viewer_reflects_namespace_registration() -> None:
    registry = EntityViewerRegistry()
    registry.register("story_bible", lambda _entity_id: None)

    assert registry.has_viewer("story_bible.character") is True
    assert registry.has_viewer("manuscript.node") is False


def test_duplicate_namespace_raises() -> None:
    registry = EntityViewerRegistry()
    registry.register("story_bible", lambda _entity_id: None)

    with pytest.raises(DuplicateViewerError):
        registry.register("story_bible", lambda _entity_id: None)


def test_unregister_removes_the_handler() -> None:
    registry = EntityViewerRegistry()
    registry.register("story_bible", lambda _entity_id: None)

    registry.unregister("story_bible")

    assert registry.reveal("story_bible.character", uuid4()) is False


def test_a_raising_handler_is_isolated_and_still_counts_as_handled() -> None:
    registry = EntityViewerRegistry()

    def _boom(_entity_id) -> None:
        raise RuntimeError("simulated failure")

    registry.register("story_bible", _boom)

    handled = registry.reveal("story_bible.character", uuid4())

    assert handled is True  # a handler existed and was invoked, even though it raised
