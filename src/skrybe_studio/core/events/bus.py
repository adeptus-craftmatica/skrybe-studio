"""Synchronous, typed, error-isolated publish/subscribe event bus.

Dispatch is keyed by the concrete `Event` subclass. Handlers are called
synchronously and in registration order. A subscriber that raises is
logged and isolated - it never prevents other subscribers, or the
publisher, from continuing.

The public surface (`subscribe`/`unsubscribe`/`publish`) is intentionally
small so that an async or queued implementation could be substituted
later without changing plugin code.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import TypeVar

from skrybe_studio.core.contracts.event import Event

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=Event)
EventHandler = Callable[[E], None]


class EventBus:
    """In-process synchronous event bus."""

    def __init__(self) -> None:
        self._subscribers: dict[type[Event], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[E], handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)
        logger.debug("Subscribed %r to %s", handler, event_type.__name__)

    def unsubscribe(self, event_type: type[E], handler: EventHandler) -> None:
        handlers = self._subscribers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)
            logger.debug("Unsubscribed %r from %s", handler, event_type.__name__)

    def publish(self, event: Event) -> None:
        event_type = type(event)
        handlers = list(self._subscribers.get(event_type, ()))
        logger.debug("Publishing %s to %d subscriber(s)", event_type.__name__, len(handlers))
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Unhandled error in subscriber %r for event %s", handler, event_type.__name__
                )
