"""`project.json` schema: only lightweight project metadata lives here.

Entities, relationships, plugin state, and all feature data live in
`project.db` - `project.json` is deliberately small and never grows into
a catch-all document.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProjectMetadata(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    app_version: str = "0.1.0"
    format_version: int = 1
    enabled_plugins: list[str] = Field(default_factory=list)
