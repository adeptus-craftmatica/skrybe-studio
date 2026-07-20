"""The Asset Library plugin's domain model. `Asset.id` is also its shared `Entity` ID.

`stored_filename` is a content-safe, UUID-based name inside the project's
managed `assets/` directory - never an absolute external path. The
original filename is preserved separately for display.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

ENTITY_TYPE = "assets.asset"
PLUGIN_ID = "com.adeptus-craftmatica.skrybe.assets"


@dataclass(frozen=True, slots=True)
class Asset:
    id: UUID
    original_filename: str
    stored_filename: str
    mime_type: str
    size_bytes: int
    content_hash: str
    imported_at: datetime
    tags: tuple[str, ...]
