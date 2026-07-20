"""Contributes manuscript titles, synopses, tags, and document content to shared search."""

from __future__ import annotations

from uuid import UUID

from skrybe_studio.core.search.contracts import SearchResult
from skrybe_studio.plugins.manuscript.domain.models import PLUGIN_ID
from skrybe_studio.plugins.manuscript.infrastructure.repositories import ManuscriptRepository


class ManuscriptSearchProvider:
    def __init__(self, repository: ManuscriptRepository) -> None:
        self._repository = repository

    def search(self, query: str) -> list[SearchResult]:
        return self.search_scoped(query, manuscript_id=None)

    def search_scoped(self, query: str, *, manuscript_id: UUID | None) -> list[SearchResult]:
        results: list[SearchResult] = []
        seen: set[UUID] = set()

        for node in self._repository.search_nodes(query, manuscript_id=manuscript_id):
            seen.add(node.id)
            snippet = node.synopsis[:140] if node.synopsis else ", ".join(node.tags)
            results.append(
                SearchResult(
                    entity_id=node.id,
                    entity_type=node.entity_type,
                    title=node.title,
                    snippet=snippet,
                    plugin_owner=PLUGIN_ID,
                )
            )

        for node in self._repository.search_content(query, manuscript_id=manuscript_id):
            if node.id in seen:
                continue
            seen.add(node.id)
            results.append(
                SearchResult(
                    entity_id=node.id,
                    entity_type=node.entity_type,
                    title=node.title,
                    snippet=self._repository.content_snippet(node.id, query),
                    plugin_owner=PLUGIN_ID,
                )
            )
        return results
