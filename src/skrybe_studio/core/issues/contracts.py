"""Contracts for cross-plugin deterministic integrity reporting.

This is a small, generic foundation - not a continuity checker. It only
describes the *shape* of an issue and how a plugin contributes them; the
actual rule logic (e.g. "a relationship points at an archived entity")
belongs entirely to whichever plugin can evaluate it, exactly like
`SearchProvider`/`SearchService` already separate "what a result looks
like" from "how a plugin finds one."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class IssueSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Issue:
    id: UUID
    severity: IssueSeverity
    rule_id: str
    plugin_owner: str
    entity_ids: tuple[UUID, ...]
    title: str
    description: str
    created_at: datetime
    suggested_resolution: str | None = None
    dismissed: bool = False
    resolved: bool = False
    metadata: dict[str, object] = field(default_factory=dict)


class IssueProvider(Protocol):
    """A plugin-owned contributor of deterministic integrity issues.

    `check()` re-evaluates the plugin's own rules from scratch each call -
    providers are expected to derive a stable `Issue.id` from `rule_id` plus
    the affected entity IDs (e.g. a deterministic UUID5) so the same
    underlying problem is recognized as "the same issue" across repeated
    runs, letting a caller preserve dismissed/resolved state by matching IDs
    rather than this contract mandating a specific persistence mechanism.
    """

    def check(self) -> list[Issue]: ...
