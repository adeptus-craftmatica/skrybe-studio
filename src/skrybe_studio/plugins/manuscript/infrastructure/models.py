"""Manuscript-owned tables. Uses its own declarative base, independent of the core's."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ManuscriptBase(DeclarativeBase):
    """Declarative base for tables owned by the Manuscript plugin."""


class ManuscriptNodeRecord(ManuscriptBase):
    __tablename__ = "manuscript_node"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    manuscript_id: Mapped[uuid.UUID] = mapped_column(index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("manuscript_node.id"), index=True, default=None
    )
    node_type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(512))
    sort_order: Mapped[float] = mapped_column(Float)
    synopsis: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    label: Mapped[str] = mapped_column(String(128), default="")
    icon_id: Mapped[str | None] = mapped_column(String(64), default=None)
    include_in_compile: Mapped[bool] = mapped_column(Boolean, default=True)
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    target_word_count: Mapped[int | None] = mapped_column(Integer, default=None)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class ManuscriptDocumentContentRecord(ManuscriptBase):
    """One-to-one with a text-bearing `ManuscriptNodeRecord`."""

    __tablename__ = "manuscript_document_content"

    node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("manuscript_node.id"), primary_key=True)
    content_json: Mapped[str] = mapped_column(Text, default="[]")
    plain_text: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ManuscriptSnapshotRecord(ManuscriptBase):
    __tablename__ = "manuscript_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("manuscript_node.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    name: Mapped[str] = mapped_column(String(256), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    content_json: Mapped[str] = mapped_column(Text)
    plain_text: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)


class ManuscriptDailyProgressRecord(ManuscriptBase):
    __tablename__ = "manuscript_daily_progress"
    __table_args__ = (UniqueConstraint("manuscript_id", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    manuscript_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("manuscript_node.id"), index=True)
    day: Mapped[date] = mapped_column(Date)
    net_word_delta: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
