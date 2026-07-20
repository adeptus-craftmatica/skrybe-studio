"""Shared search abstraction: plugins contribute searchable content."""

from skrybe_studio.core.search.contracts import SearchProvider, SearchResult
from skrybe_studio.core.search.service import SearchService

__all__ = ["SearchProvider", "SearchResult", "SearchService"]
