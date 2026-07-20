"""A small, domain-neutral capability for resolving asset references across plugins.

This is a deliberate, minimal evolution of the core (see
`docs/manuscript-plugin.md`'s "Asset integration" section for the
rationale): the Manuscript plugin needs to resolve a cover/reference
image without importing the Asset Library plugin's implementation
classes. Nothing here is manuscript-specific - any plugin that owns
image-like assets could implement it, and any plugin that wants to
reference one can consume it via `core/services`, exactly like any
other cross-plugin capability.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID


class AssetLookup(Protocol):
    """Read-only asset resolution. Implemented by the Asset Library plugin,
    registered into `core/services` during `activate()`."""

    def asset_exists(self, asset_id: UUID) -> bool: ...

    def asset_title(self, asset_id: UUID) -> str | None: ...

    def resolve_thumbnail(self, asset_id: UUID) -> Path | None: ...

    def list_assets(self) -> list[tuple[UUID, str]]:
        """Every available asset as `(asset_id, display_title)`, for simple pickers."""
        ...
