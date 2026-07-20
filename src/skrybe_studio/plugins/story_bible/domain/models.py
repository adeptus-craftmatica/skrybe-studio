"""Story Bible's own domain model. Nothing here is Qt- or SQLAlchemy-aware.

`StoryBibleEntity.id` is also the shared core `Entity` ID (same pattern as
every other plugin: the plugin's own primary key doubles as the entity ID,
so there is no second ID space to keep in sync).

**Authoritative title**: `StoryBibleEntity.primary_name` is authoritative;
the shared `core_entities.title` is kept in sync with it by
`EntityService.rename()` every time `primary_name` changes (in
`EntityCatalogService`/`StoryBibleEntityService`), exactly like Notes keeps
`Note.title` and the shared entity title in sync. Nothing should ever read
`primary_name` from the shared entity - always from this record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from skrybe_studio.plugins.story_bible.domain.enums import FieldType

PLUGIN_ID = "com.adeptus-craftmatica.skrybe.story_bible"
NAMESPACE = "story_bible"


def entity_type_id_for(type_key: str) -> str:
    """The core-registry-facing entity type ID for a given project-local type key.

    e.g. `entity_type_id_for("character")` -> `"story_bible.character"`. Both
    built-in and custom types go through this - a custom type's `type_key`
    is just the user's own machine-safe key instead of a built-in name.
    """
    return f"{NAMESPACE}.{type_key}"


@dataclass(frozen=True, slots=True)
class EntityType:
    """A row in `story_bible_entity_type` - built-in or project-local custom.

    Built-in types are seeded once per project (see
    `application/builtins.py`) and are ordinary rows from that point on:
    editing a built-in type's display name/icon/fields in one project never
    affects another project or a future new project's seed.
    """

    id: UUID
    type_key: str
    is_builtin: bool
    display_name: str
    plural_display_name: str
    created_at: datetime
    updated_at: datetime
    description: str = ""
    icon_id: str | None = None
    color_token: str | None = None
    user_instantiable: bool = True
    user_extensible: bool = True
    user_archivable: bool = True
    archived_at: datetime | None = None

    @property
    def entity_type_id(self) -> str:
        return entity_type_id_for(self.type_key)

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    """One field on an entity type. `internal_key` is stable and referenced
    by templates' `field_values`; stored entity field *values* reference
    this row by `id` (a UUID), not by `internal_key` - so renaming a field's
    `internal_key` or `display_label` never touches already-stored values.
    """

    id: UUID
    entity_type_id: UUID
    """FK to `EntityTypeRecord.id` (not the `story_bible.<key>` string ID)."""
    internal_key: str
    display_label: str
    field_type: FieldType
    sort_order: float
    created_at: datetime
    updated_at: datetime
    description: str = ""
    required: bool = False
    default_value: object | None = None
    choice_options: tuple[str, ...] = field(default_factory=tuple)
    section: str | None = None
    searchable: bool = False
    display_in_list: bool = False
    display_in_card: bool = False
    active: bool = True


@dataclass(frozen=True, slots=True)
class StoryBibleEntity:
    id: UUID
    entity_type_id: UUID
    """FK to `EntityTypeRecord.id`."""
    primary_name: str
    created_at: datetime
    updated_at: datetime
    summary: str = ""
    aliases: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""
    status: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    archived_at: datetime | None = None

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None


@dataclass(frozen=True, slots=True)
class FieldValue:
    id: UUID
    entity_id: UUID
    field_definition_id: UUID
    value: object | None


@dataclass(frozen=True, slots=True)
class EntityTemplate:
    id: UUID
    entity_type_id: UUID
    """FK to `EntityTypeRecord.id`."""
    name: str
    is_builtin: bool
    created_at: datetime
    updated_at: datetime
    field_values: dict[str, object] = field(default_factory=dict)
    """Keyed by field `internal_key`, applied to a new entity's field values
    at creation time only - not a live link to the field definitions."""
