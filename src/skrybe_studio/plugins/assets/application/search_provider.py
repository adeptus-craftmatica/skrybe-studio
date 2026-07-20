"""Contributes asset filenames and tags to the shared search service."""

from __future__ import annotations

from skrybe_studio.core.search.contracts import SearchResult
from skrybe_studio.plugins.assets.domain.asset import ENTITY_TYPE, PLUGIN_ID
from skrybe_studio.plugins.assets.infrastructure.repository import AssetRepository


class AssetsSearchProvider:
    def __init__(self, repository: AssetRepository) -> None:
        self._repository = repository

    def search(self, query: str) -> list[SearchResult]:
        return [
            SearchResult(
                entity_id=asset.id,
                entity_type=ENTITY_TYPE,
                title=asset.original_filename,
                snippet=", ".join(asset.tags),
                plugin_owner=PLUGIN_ID,
            )
            for asset in self._repository.search(query)
        ]
