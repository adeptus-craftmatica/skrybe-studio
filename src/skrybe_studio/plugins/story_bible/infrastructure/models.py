"""Story Bible-owned tables. Uses its own declarative base, independent of
the core's and of every other plugin's.

Every entity type - built-in or custom - is a real row in
`story_bible_entity_type` with a real UUID primary key, so
`FieldDefinition.entity_type_id`/`StoryBibleEntity.entity_type_id` can be
genuine foreign keys rather than soft string references. The core-facing
type ID string (`story_bible.<type_key>`) is derived from `type_key`, never
stored redundantly.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class StoryBibleBase(DeclarativeBase):
    """Declarative base for tables owned by the Story Bible plugin."""


class EntityTypeRecord(StoryBibleBase):
    __tablename__ = "story_bible_entity_type"
    __table_args__ = (UniqueConstraint("type_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    type_key: Mapped[str] = mapped_column(String(128))
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    display_name: Mapped[str] = mapped_column(String(256))
    plural_display_name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text, default="")
    icon_id: Mapped[str | None] = mapped_column(String(64), default=None)
    color_token: Mapped[str | None] = mapped_column(String(64), default=None)
    user_instantiable: Mapped[bool] = mapped_column(Boolean, default=True)
    user_extensible: Mapped[bool] = mapped_column(Boolean, default=True)
    user_archivable: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class FieldDefinitionRecord(StoryBibleBase):
    __tablename__ = "story_bible_field_definition"
    __table_args__ = (UniqueConstraint("entity_type_id", "internal_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    entity_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("story_bible_entity_type.id"), index=True
    )
    internal_key: Mapped[str] = mapped_column(String(128))
    display_label: Mapped[str] = mapped_column(String(256))
    field_type: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text, default="")
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    default_value_json: Mapped[Any | None] = mapped_column(JSON, default=None)
    choice_options_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    sort_order: Mapped[float] = mapped_column(Float)
    section: Mapped[str | None] = mapped_column(String(128), default=None)
    searchable: Mapped[bool] = mapped_column(Boolean, default=False)
    display_in_list: Mapped[bool] = mapped_column(Boolean, default=False)
    display_in_card: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StoryBibleEntityRecord(StoryBibleBase):
    __tablename__ = "story_bible_entity"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    entity_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("story_bible_entity_type.id"), index=True
    )
    primary_name: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str] = mapped_column(Text, default="")
    aliases_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(64), default="")
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, index=True
    )


class FieldValueRecord(StoryBibleBase):
    __tablename__ = "story_bible_field_value"
    __table_args__ = (UniqueConstraint("entity_id", "field_definition_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("story_bible_entity.id"), index=True)
    field_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("story_bible_field_definition.id"), index=True
    )
    value_json: Mapped[Any | None] = mapped_column(JSON, default=None)


class TemplateRecord(StoryBibleBase):
    __tablename__ = "story_bible_template"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    entity_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("story_bible_entity_type.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(256))
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    field_values_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
