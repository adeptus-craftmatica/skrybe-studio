"""Declarative workspace description.

A `Workspace` references panels and commands only by registered string
ID - never by importing a plugin's concrete panel or command classes.
This keeps workspaces decoupled from any specific plugin implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DockArea = str  # "left" | "right" | "bottom"


@dataclass(frozen=True, slots=True)
class PanelPlacement:
    panel_id: str
    area: DockArea = "left"


@dataclass(frozen=True, slots=True)
class Workspace:
    id: str
    title: str
    central_panel_id: str | None = None
    panels: tuple[PanelPlacement, ...] = field(default_factory=tuple)
    toolbar_command_ids: tuple[str, ...] = field(default_factory=tuple)
