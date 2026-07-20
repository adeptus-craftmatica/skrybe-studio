"""A generic "where did I just go" record for cross-plugin Back/Forward.

Deliberately entity-ID-based rather than panel- or workspace-based: any
plugin can push a visit without the navigation history needing to know
which workspace, panel, or widget class is involved - resolving a target
back into something visible on screen is `core/navigation`'s
`EntityViewerRegistry`'s job, not this contract's.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class NavigationTarget:
    entity_id: UUID
    entity_type: str
    source_plugin_id: str | None = None
