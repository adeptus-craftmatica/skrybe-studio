"""Contributes Story Bible entities to the shared cross-plugin search."""

from __future__ import annotations

from skrybe_studio.core.search.contracts import SearchResult
from skrybe_studio.plugins.story_bible.application.entity_service import StoryBibleEntityService
from skrybe_studio.plugins.story_bible.application.schema_service import SchemaService
from skrybe_studio.plugins.story_bible.domain.models import PLUGIN_ID


class StoryBibleSearchProvider:
    def __init__(self, entities: StoryBibleEntityService, schema: SchemaService) -> None:
        self._entities = entities
        self._schema = schema

    def search(self, query: str) -> list[SearchResult]:
        types_by_id = {t.id: t for t in self._schema.list_types(include_archived=True)}
        results = []
        for entity in self._entities.search(query):
            entity_type = types_by_id.get(entity.entity_type_id)
            entity_type_id = (
                entity_type.entity_type_id if entity_type is not None else "story_bible.unknown"
            )
            snippet = entity.summary or ", ".join(entity.aliases) or entity.status
            results.append(
                SearchResult(
                    entity_id=entity.id,
                    entity_type=entity_type_id,
                    title=entity.primary_name,
                    snippet=snippet,
                    plugin_owner=PLUGIN_ID,
                )
            )
        return results
