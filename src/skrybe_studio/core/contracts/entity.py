"""The Entity contract: a globally addressable project object.

Every object plugins want to reference, link, search, or display in a
shared panel (notes, assets, and future story-bible objects, timeline
events, characters, and so on) is represented as an Entity. The core only
ever sees this generic shape - it never knows what a "note" or "asset" is.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Entity(BaseModel):
    """A globally addressable, softly-deletable project object."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    entity_type: str
    title: str
    plugin_owner: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
