"""A generic description of "what does this relationship type mean," for any
plugin that wants to render or validate a relationship it doesn't own - a
graph view showing an edge, a relationship editor picking a type, a
backlink list picking a label - without importing the defining plugin.

Canonical relationship *records* (`core/contracts/relationship.py`,
`RelationshipService`) already work this way, and were proven for real in
0.2 (Manuscript's `manuscript.cover_asset` relationship, read generically by
the Asset Library's details panel). This is the same idea applied to
relationship *type metadata*: any plugin can define a type, any plugin can
look up its display shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RelationshipTypeDefinition:
    """Metadata about a relationship type, registered by the plugin that
    defines it. Built-in types are registered at `register()` time;
    project-local custom types are registered/unregistered per project,
    same rationale as `EntityTypeDefinition`.
    """

    type_id: str
    display_label: str
    reverse_label: str
    owning_plugin_id: str
    directed: bool = True
    allowed_source_types: tuple[str, ...] = field(default_factory=tuple)
    """Entity type IDs allowed as the source. Empty means "any type"."""
    allowed_target_types: tuple[str, ...] = field(default_factory=tuple)
    """Entity type IDs allowed as the target. Empty means "any type"."""
    cardinality: str = "many_to_many"
    """One of "one_to_one", "one_to_many", or "many_to_many" - guidance for
    editing UI, not an enforced database constraint."""
    color_token: str | None = None
    description: str = ""
    user_editable: bool = True
