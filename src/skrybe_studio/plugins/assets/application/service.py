"""Imports files into the project's managed asset directory and tracks their metadata.

Hashing and thumbnailing run as a background `Job` so large files never
block the UI thread. Duplicate detection happens once the SHA-256 hash is
known (after the background copy completes) rather than before, so
importing several large files never stalls on synchronous hashing.
"""

from __future__ import annotations

import logging
import mimetypes
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from skrybe_studio.core.entities.service import EntityService
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.core.jobs.manager import JobManager
from skrybe_studio.plugins.assets.application.events import (
    AssetImported,
    AssetMetadataChanged,
    AssetRemoved,
)
from skrybe_studio.plugins.assets.application.jobs import AssetImportJob, AssetImportResult
from skrybe_studio.plugins.assets.domain.asset import ENTITY_TYPE, PLUGIN_ID, Asset
from skrybe_studio.plugins.assets.infrastructure.repository import AssetRepository

logger = logging.getLogger(__name__)


class AssetsService:
    def __init__(
        self,
        repository: AssetRepository,
        entities: EntityService,
        events: EventBus,
        jobs: JobManager,
        assets_dir: Path,
        cache_dir: Path,
    ) -> None:
        self._repository = repository
        self._entities = entities
        self._events = events
        self._jobs = jobs
        self._assets_dir = assets_dir
        self._cache_dir = cache_dir

    def import_asset(
        self,
        source_path: Path,
        *,
        on_imported: Callable[[UUID], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> UUID:
        """Submits a background copy+hash+thumbnail job; returns the pending asset ID immediately."""
        asset_id = uuid4()
        stored_filename = f"{asset_id}{source_path.suffix.lower()}"
        job = AssetImportJob(
            asset_id, source_path, self._assets_dir, self._cache_dir, stored_filename
        )

        def _handle_success(result: object) -> None:
            assert isinstance(result, AssetImportResult)
            created = self._finish_import(result, source_path)
            if created and on_imported is not None:
                on_imported(result.asset_id)

        def _handle_error(message: str) -> None:
            logger.error("Failed to import asset from %s: %s", source_path, message)
            if on_error is not None:
                on_error(message)

        self._jobs.submit(job, on_success=_handle_success, on_error=_handle_error)
        return asset_id

    def _finish_import(self, result: AssetImportResult, source_path: Path) -> bool:
        existing = self._repository.find_by_hash(result.content_hash)
        if existing is not None:
            logger.info(
                "Duplicate content detected for '%s' (matches existing asset %s); discarding copy",
                source_path.name,
                existing.id,
            )
            result.stored_path.unlink(missing_ok=True)
            if result.thumbnail_path is not None:
                result.thumbnail_path.unlink(missing_ok=True)
            return False

        mime_type, _ = mimetypes.guess_type(source_path.name)
        asset = Asset(
            id=result.asset_id,
            original_filename=source_path.name,
            stored_filename=result.stored_path.name,
            mime_type=mime_type or "application/octet-stream",
            size_bytes=result.size_bytes,
            content_hash=result.content_hash,
            imported_at=datetime.now(UTC),
            tags=(),
        )
        self._entities.create(
            entity_type=ENTITY_TYPE,
            title=asset.original_filename,
            plugin_owner=PLUGIN_ID,
            entity_id=asset.id,
        )
        self._repository.add(asset)
        logger.info("Imported asset '%s' (%s)", asset.original_filename, asset.id)
        self._events.publish(
            AssetImported(asset_id=asset.id, original_filename=asset.original_filename)
        )
        return True

    def remove_asset(self, asset_id: UUID) -> bool:
        asset = self._repository.get(asset_id)
        if asset is None:
            return False
        self.resolve_path(asset).unlink(missing_ok=True)
        self._thumbnail_file_path(asset_id).unlink(missing_ok=True)
        self._repository.delete(asset_id)
        self._entities.soft_delete(asset_id)
        logger.info("Removed asset '%s' (%s)", asset.original_filename, asset_id)
        self._events.publish(AssetRemoved(asset_id=asset_id))
        return True

    def set_tags(self, asset_id: UUID, tags: tuple[str, ...]) -> Asset | None:
        asset = self._repository.update(asset_id, tags=tags)
        if asset is None:
            return None
        self._events.publish(AssetMetadataChanged(asset_id=asset_id))
        return asset

    def get_asset(self, asset_id: UUID) -> Asset | None:
        return self._repository.get(asset_id)

    def list_assets(self) -> list[Asset]:
        return self._repository.list()

    def search_assets(self, query: str) -> list[Asset]:
        return self._repository.search(query)

    def resolve_path(self, asset: Asset) -> Path:
        return self._assets_dir / asset.stored_filename

    def is_missing(self, asset: Asset) -> bool:
        return not self.resolve_path(asset).exists()

    def thumbnail_path(self, asset_id: UUID) -> Path | None:
        path = self._thumbnail_file_path(asset_id)
        return path if path.exists() else None

    def _thumbnail_file_path(self, asset_id: UUID) -> Path:
        return self._cache_dir / f"{asset_id}.png"
