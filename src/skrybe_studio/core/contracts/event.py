"""The Event contract: a typed payload published on the event bus.

Subclass `Event` for every distinct event a plugin wants to publish, e.g.
`NoteCreated`, `AssetImported`. The bus dispatches by the concrete class,
so subscribers register for exactly the event types they care about.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Event:
    """Base class for all typed event payloads."""
