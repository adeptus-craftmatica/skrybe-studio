"""Lightweight writing goals: per-node targets (stored directly on the node) plus
an optional daily target and net-word-delta progress tracking for the manuscript.

Per-document/subtree/whole-manuscript targets are all just
`ManuscriptNode.target_word_count` - a chapter's target is exactly as
meaningful as a scene's or the manuscript root's. The daily target is
manuscript-wide, stored in the root node's metadata dict rather than a
dedicated column since it's the one goal that isn't "this node's target".
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from skrybe_studio.plugins.manuscript.domain.models import DailyProgress
from skrybe_studio.plugins.manuscript.infrastructure.repositories import (
    ManuscriptRepository,
    ProgressRepository,
)

_DAILY_TARGET_KEY = "daily_target_word_count"


class GoalsService:
    def __init__(self, repository: ManuscriptRepository, progress: ProgressRepository) -> None:
        self._repository = repository
        self._progress = progress

    def get_daily_target(self, manuscript_id: UUID) -> int | None:
        root = self._repository.get_node(manuscript_id)
        if root is None:
            return None
        value = root.metadata.get(_DAILY_TARGET_KEY)
        return value if isinstance(value, int) else None

    def set_daily_target(self, manuscript_id: UUID, target: int | None) -> None:
        root = self._repository.get_node(manuscript_id)
        if root is None:
            return
        metadata = dict(root.metadata)
        if target is None:
            metadata.pop(_DAILY_TARGET_KEY, None)
        else:
            metadata[_DAILY_TARGET_KEY] = target
        self._repository.update_node(manuscript_id, metadata=metadata)

    def today_progress(self, manuscript_id: UUID) -> DailyProgress | None:
        return self._progress.get_for_day(manuscript_id, datetime.now(UTC).date())

    def recent_progress(self, manuscript_id: UUID, *, limit: int = 30) -> list[DailyProgress]:
        return self._progress.list_recent(manuscript_id, limit=limit)
