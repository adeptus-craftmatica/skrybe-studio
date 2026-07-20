"""Contracts for cross-plugin search contribution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SearchResult:
    entity_id: UUID
    entity_type: str
    title: str
    snippet: str
    plugin_owner: str


class SearchProvider(Protocol):
    """A plugin-owned contributor of searchable content.

    This iteration's implementations run simple SQLite `LIKE` queries; the
    interface says nothing about that, so a full-text index can replace
    a provider's internals later without touching registration.
    """

    def search(self, query: str) -> list[SearchResult]: ...
