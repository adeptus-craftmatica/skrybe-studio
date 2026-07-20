"""Persistence for `Asset`s. The application layer never touches SQL directly."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from skrybe_studio.core.storage.database import Database
from skrybe_studio.plugins.assets.domain.asset import Asset
from skrybe_studio.plugins.assets.infrastructure.models import AssetRecord


def _to_asset(record: AssetRecord) -> Asset:
    return Asset(
        id=record.id,
        original_filename=record.original_filename,
        stored_filename=record.stored_filename,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        content_hash=record.content_hash,
        imported_at=record.imported_at,
        tags=tuple(record.tags_json or []),
    )


class AssetRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def add(self, asset: Asset) -> None:
        with self._database.session() as session:
            session.add(
                AssetRecord(
                    id=asset.id,
                    original_filename=asset.original_filename,
                    stored_filename=asset.stored_filename,
                    mime_type=asset.mime_type,
                    size_bytes=asset.size_bytes,
                    content_hash=asset.content_hash,
                    imported_at=asset.imported_at,
                    tags_json=list(asset.tags),
                )
            )

    def get(self, asset_id: UUID) -> Asset | None:
        with self._database.session() as session:
            record = session.get(AssetRecord, asset_id)
            return _to_asset(record) if record is not None else None

    def list(self) -> list[Asset]:
        with self._database.session() as session:
            stmt = select(AssetRecord).order_by(AssetRecord.imported_at.desc())
            return [_to_asset(record) for record in session.scalars(stmt)]

    def find_by_hash(self, content_hash: str) -> Asset | None:
        with self._database.session() as session:
            stmt = select(AssetRecord).where(AssetRecord.content_hash == content_hash)
            record = session.scalars(stmt).first()
            return _to_asset(record) if record is not None else None

    def update(self, asset_id: UUID, *, tags: tuple[str, ...] | None = None) -> Asset | None:
        with self._database.session() as session:
            record = session.get(AssetRecord, asset_id)
            if record is None:
                return None
            if tags is not None:
                record.tags_json = list(tags)
            session.flush()
            return _to_asset(record)

    def delete(self, asset_id: UUID) -> bool:
        with self._database.session() as session:
            record = session.get(AssetRecord, asset_id)
            if record is None:
                return False
            session.delete(record)
            return True

    def search(self, query: str) -> list[Asset]:
        """Simple substring match over filename and tags.

        Tags are stored as a JSON list, so this filters in Python rather
        than in SQL - acceptable at this iteration's scale, and easy to
        replace with a real index later without changing the interface.
        """
        needle = query.lower()
        with self._database.session() as session:
            records = session.scalars(select(AssetRecord))
            return [
                _to_asset(record)
                for record in records
                if needle in record.original_filename.lower()
                or any(needle in tag.lower() for tag in (record.tags_json or []))
            ]
