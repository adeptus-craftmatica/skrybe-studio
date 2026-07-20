"""A small typed service locator plugins use to publish and consume
narrow service interfaces without importing one another's implementation
classes.

A plugin that wants to expose a capability defines a `Protocol` (or plain
ABC) for it, registers an instance against that interface type, and other
plugins resolve it the same way. Nothing here couples one feature plugin
to another's concrete classes.
"""

from __future__ import annotations

import logging
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceContainer:
    """Registers and resolves service instances keyed by interface type."""

    def __init__(self) -> None:
        self._services: dict[type, object] = {}

    def register(self, interface: type[T], instance: T) -> None:
        self._services[interface] = instance
        logger.debug("Registered service for %s", interface.__name__)

    def unregister(self, interface: type[T]) -> None:
        self._services.pop(interface, None)

    def get(self, interface: type[T]) -> T | None:
        instance = self._services.get(interface)
        return instance  # type: ignore[return-value]

    def require(self, interface: type[T]) -> T:
        instance = self.get(interface)
        if instance is None:
            raise KeyError(f"No service registered for {interface.__name__}")
        return instance

    def has(self, interface: type) -> bool:
        return interface in self._services
