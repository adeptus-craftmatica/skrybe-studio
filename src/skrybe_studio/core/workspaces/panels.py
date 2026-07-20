"""Maps a stable panel ID to a widget factory.

Workspaces and the main window create panels by ID through this registry
so they never need to import a plugin's concrete panel class.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)

PanelFactory = Callable[[], QWidget]


class DuplicatePanelError(RuntimeError):
    """Raised when two panels are registered under the same ID."""


class PanelRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, PanelFactory] = {}
        self._titles: dict[str, str] = {}

    def register(self, panel_id: str, title: str, factory: PanelFactory) -> None:
        if panel_id in self._factories:
            raise DuplicatePanelError(f"Panel '{panel_id}' is already registered")
        self._factories[panel_id] = factory
        self._titles[panel_id] = title
        logger.debug("Registered panel '%s'", panel_id)

    def create(self, panel_id: str) -> QWidget:
        factory = self._factories.get(panel_id)
        if factory is None:
            raise KeyError(f"Unknown panel '{panel_id}'")
        return factory()

    def title_for(self, panel_id: str) -> str:
        return self._titles.get(panel_id, panel_id)

    def known_panel_ids(self) -> list[str]:
        return list(self._factories.keys())
