"""A generic description of "what kind of entity is this," for any plugin
that wants to introspect an entity type it doesn't own - showing an icon
next to a search result, listing available types in a creation picker,
labeling a backlink - without importing the owning plugin.

Nothing here is specific to story writing: a future project-management
plugin's "Task" or "Milestone" type would describe itself the same way.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EntityTypeDefinition:
    """Metadata about an entity type, registered by the plugin that owns it.

    Built-in types (e.g. Story Bible's `story_bible.character`) are
    registered once, at `register()` time - they're static, code-defined
    shapes. Project-local custom types (user-created, no code involved) are
    registered/unregistered as their owning plugin activates/deactivates for
    a given project, since they're project data, not application code.
    """

    type_id: str
    display_name: str
    plural_display_name: str
    owning_plugin_id: str
    icon_id: str | None = None
    color_token: str | None = None
    description: str = ""
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    user_instantiable: bool = True
    user_extensible: bool = True
    user_archivable: bool = True
    preferred_viewer_id: str | None = None
