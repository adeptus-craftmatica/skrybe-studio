"""Implements the shared `core.contracts.AssetLookup` capability over `AssetsService`.

Registered into the shared service container during `activate()` so
other plugins (e.g. Manuscript) can resolve an asset reference without
importing anything from this plugin's implementation.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from skrybe_studio.plugins.assets.application.service import AssetsService


class AssetLookupAdapter:
    def __init__(self, service: AssetsService) -> None:
        self._service = service

    def asset_exists(self, asset_id: UUID) -> bool:
        return self._service.get_asset(asset_id) is not None

    def asset_title(self, asset_id: UUID) -> str | None:
        asset = self._service.get_asset(asset_id)
        return asset.original_filename if asset is not None else None

    def resolve_thumbnail(self, asset_id: UUID) -> Path | None:
        return self._service.thumbnail_path(asset_id)

    def list_assets(self) -> list[tuple[UUID, str]]:
        return [(asset.id, asset.original_filename) for asset in self._service.list_assets()]
