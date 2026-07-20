from __future__ import annotations

from skrybe_studio.plugins.story_bible.application.entity_service import StoryBibleEntityService
from skrybe_studio.plugins.story_bible.application.schema_service import SchemaService
from skrybe_studio.plugins.story_bible.application.search_provider import StoryBibleSearchProvider


def test_search_returns_results_shaped_for_the_shared_search_service(
    schema: SchemaService,
    story_bible_entities: StoryBibleEntityService,
    search_provider: StoryBibleSearchProvider,
) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    ship = story_bible_entities.create_entity(
        entity_type.id, "The Nautilus", summary="A submarine of note."
    )

    results = search_provider.search("nautilus")

    assert len(results) == 1
    result = results[0]
    assert result.entity_id == ship.id
    assert result.entity_type == "story_bible.spaceship"
    assert result.title == "The Nautilus"
    assert result.snippet == "A submarine of note."
    assert result.plugin_owner == "com.adeptus-craftmatica.skrybe.story_bible"


def test_search_with_no_matches_returns_empty(search_provider: StoryBibleSearchProvider) -> None:
    assert search_provider.search("nonexistent") == []
