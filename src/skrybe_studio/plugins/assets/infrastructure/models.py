"""Asset-Library-owned tables. Uses its own declarative base, independent of the core's."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class AssetsBase(DeclarativeBase):
    """Declarative base for tables owned by the Asset Library plugin."""


class AssetRecord(AssetsBase):
    __tablename__ = "assets_asset"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(512))
    stored_filename: Mapped[str] = mapped_column(String(256))
    mime_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list)
