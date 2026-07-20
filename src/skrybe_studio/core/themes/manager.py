"""Resolves the active theme mode (light / dark / system) to design tokens."""

from __future__ import annotations

import logging
from enum import StrEnum

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication, Qt

from skrybe_studio.core.themes.tokens import DARK_TOKENS, LIGHT_TOKENS, DesignTokens

logger = logging.getLogger(__name__)


class ThemeMode(StrEnum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


def _system_prefers_dark() -> bool:
    app = QGuiApplication.instance()
    if not isinstance(app, QGuiApplication):
        return False
    return app.styleHints().colorScheme() == Qt.ColorScheme.Dark


class ThemeManager(QObject):
    """Tracks the requested `ThemeMode` and exposes the resolved `DesignTokens`."""

    theme_changed = Signal(object)

    def __init__(self, mode: ThemeMode = ThemeMode.SYSTEM) -> None:
        super().__init__()
        self._mode = mode

    @property
    def mode(self) -> ThemeMode:
        return self._mode

    def set_mode(self, mode: ThemeMode) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        logger.info("Theme mode set to '%s'", mode.value)
        self.theme_changed.emit(self.tokens)

    @property
    def is_dark(self) -> bool:
        if self._mode == ThemeMode.DARK:
            return True
        if self._mode == ThemeMode.LIGHT:
            return False
        return _system_prefers_dark()

    @property
    def tokens(self) -> DesignTokens:
        return DARK_TOKENS if self.is_dark else LIGHT_TOKENS
