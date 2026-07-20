"""Typed events published by the Asset Library plugin."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from skrybe_studio.core.contracts.event import Event


@dataclass(frozen=True, slots=True)
class AssetImported(Event):
    asset_id: UUID
    original_filename: str


@dataclass(frozen=True, slots=True)
class AssetMetadataChanged(Event):
    asset_id: UUID


@dataclass(frozen=True, slots=True)
class AssetRemoved(Event):
    asset_id: UUID


@dataclass(frozen=True, slots=True)
class AssetSelectionChanged(Event):
    """UI-only event: which asset the Asset Library browser panel currently has selected."""

    asset_id: UUID | None
