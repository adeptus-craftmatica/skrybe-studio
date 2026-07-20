"""Tracks the most recently opened projects in application-scoped settings."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from skrybe_studio.core.settings.service import SettingsService

MAX_RECENT_PROJECTS = 10


class RecentProjectsStore:
    def __init__(self, settings: SettingsService) -> None:
        self._settings = settings

    def all(self) -> list[dict[str, Any]]:
        return list(self._settings.get_app("recent_projects", []))

    def record_opened(self, path: Path, name: str) -> None:
        entries = [entry for entry in self.all() if entry.get("path") != str(path)]
        entries.insert(
            0,
            {
                "path": str(path),
                "name": name,
                "last_opened": datetime.now(UTC).isoformat(),
            },
        )
        self._settings.set_app("recent_projects", entries[:MAX_RECENT_PROJECTS])

    def remove(self, path: Path) -> None:
        entries = [entry for entry in self.all() if entry.get("path") != str(path)]
        self._settings.set_app("recent_projects", entries)
