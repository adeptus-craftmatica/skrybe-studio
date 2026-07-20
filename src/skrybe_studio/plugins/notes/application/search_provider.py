"""Contributes note titles and bodies to the shared search service."""

from __future__ import annotations

from skrybe_studio.core.search.contracts import SearchResult
from skrybe_studio.plugins.notes.domain.note import ENTITY_TYPE, PLUGIN_ID
from skrybe_studio.plugins.notes.infrastructure.repository import NoteRepository


class NotesSearchProvider:
    def __init__(self, repository: NoteRepository) -> None:
        self._repository = repository

    def search(self, query: str) -> list[SearchResult]:
        return [
            SearchResult(
                entity_id=note.id,
                entity_type=ENTITY_TYPE,
                title=note.title,
                snippet=note.body[:140],
                plugin_owner=PLUGIN_ID,
            )
            for note in self._repository.search(query)
        ]
