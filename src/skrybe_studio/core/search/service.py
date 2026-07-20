"""Aggregates results from every registered `SearchProvider`."""

from __future__ import annotations

import logging

from skrybe_studio.core.search.contracts import SearchProvider, SearchResult

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self) -> None:
        self._providers: list[SearchProvider] = []

    def register_provider(self, provider: SearchProvider) -> None:
        self._providers.append(provider)

    def unregister_provider(self, provider: SearchProvider) -> None:
        if provider in self._providers:
            self._providers.remove(provider)

    def search(self, query: str) -> list[SearchResult]:
        if not query.strip():
            return []
        results: list[SearchResult] = []
        for provider in self._providers:
            try:
                results.extend(provider.search(query))
            except Exception:
                logger.exception("Search provider %r raised while searching", provider)
        return results
