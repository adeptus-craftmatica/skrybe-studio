"""Resolves how to open/reveal an entity, keyed by owning-plugin namespace.

A handler is registered once per namespace at `register()` time (namespaces
- the text before an entity type's first "." - are static; individual
entity types within a namespace, including project-local custom ones, never
need separate registration). A handler is a plain bound method on the
owning plugin instance, exactly like a `Command.is_enabled` callback: it is
expected to check its own plugin's state (e.g. "is a project open, does
this entity still exist") and no-op gracefully rather than raise, so a
disabled or not-yet-activated plugin never breaks a caller that merely
tried to reveal something.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from uuid import UUID

logger = logging.getLogger(__name__)

RevealHandler = Callable[[UUID], None]


class DuplicateViewerError(RuntimeError):
    """Raised when two handlers are registered for the same namespace."""


class EntityViewerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, RevealHandler] = {}

    def register(self, namespace: str, handler: RevealHandler) -> None:
        if namespace in self._handlers:
            raise DuplicateViewerError(f"Namespace '{namespace}' already has a reveal handler")
        self._handlers[namespace] = handler
        logger.debug("Registered entity viewer for namespace '%s'", namespace)

    def unregister(self, namespace: str) -> None:
        self._handlers.pop(namespace, None)

    def has_viewer(self, entity_type: str) -> bool:
        return _namespace_of(entity_type) in self._handlers

    def reveal(self, entity_type: str, entity_id: UUID) -> bool:
        """Looks up a handler by `entity_type`'s namespace and invokes it.

        Returns whether a handler was found - not whether it "succeeded" at
        anything in particular, since a handler that no-ops because the
        entity was deleted is still a handled reveal attempt, not a missing
        handler. A handler raising is logged and isolated, matching every
        other cross-plugin callback in this codebase (event subscribers,
        command handlers, plugin lifecycle calls).
        """
        namespace = _namespace_of(entity_type)
        handler = self._handlers.get(namespace)
        if handler is None:
            return False
        try:
            handler(entity_id)
        except Exception:
            logger.exception("Reveal handler for namespace '%s' raised", namespace)
        return True


def _namespace_of(entity_type: str) -> str:
    return entity_type.split(".", 1)[0]
