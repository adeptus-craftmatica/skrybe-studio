"""The Command contract: a user- or system-triggered action."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


def _always_enabled() -> bool:
    return True


@dataclass(frozen=True, slots=True)
class Command:
    """A registrable action, invoked by menus, toolbars, or shortcuts."""

    id: str
    title: str
    handler: Callable[[], None]
    description: str = ""
    shortcut: str | None = None
    category: str = "General"
    icon: str | None = None
    is_enabled: Callable[[], bool] = field(default=_always_enabled)
