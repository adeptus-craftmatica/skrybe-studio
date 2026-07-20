"""Cross-plugin entity navigation: reveal handlers and Back/Forward history."""

from skrybe_studio.core.navigation.service import NavigationService
from skrybe_studio.core.navigation.viewer_registry import (
    DuplicateViewerError,
    EntityViewerRegistry,
    RevealHandler,
)

__all__ = [
    "DuplicateViewerError",
    "EntityViewerRegistry",
    "NavigationService",
    "RevealHandler",
]
