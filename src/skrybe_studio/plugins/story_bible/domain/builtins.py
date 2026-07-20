"""Built-in entity types and their default field sets.

Pure data - seeded once into a project's `story_bible_entity_type`/
`story_bible_field_definition` tables the first time Story Bible activates
for that project (see `application/schema_service.py`). From that point on
they are ordinary project-local rows: a project can rename, reorder,
deactivate, or add fields to "Character" without affecting any other
project or a future project's seed, per "keep templates editable and
removable at project scope."

Field lists are deliberately modest - a fresh project should not present an
intimidating wall of fields for every built-in type. Character, Location,
Organization, and Item get the fuller shape called out in the spec;
world-flavor types without an explicit design (Culture, Species, Magic
System, Technology, Language, Historical Event, Theme) get a small,
calm starting set that a project can grow as needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from skrybe_studio.plugins.story_bible.domain.enums import FieldType


@dataclass(frozen=True, slots=True)
class BuiltinFieldSpec:
    internal_key: str
    display_label: str
    field_type: FieldType
    required: bool = False
    section: str | None = None
    searchable: bool = False
    display_in_list: bool = False
    display_in_card: bool = False


@dataclass(frozen=True, slots=True)
class BuiltinTypeSpec:
    type_key: str
    display_name: str
    plural_display_name: str
    description: str
    icon_id: str
    fields: tuple[BuiltinFieldSpec, ...] = field(default_factory=tuple)


def _f(
    key: str,
    label: str,
    field_type: FieldType,
    *,
    required: bool = False,
    section: str | None = None,
    searchable: bool = False,
    display_in_list: bool = False,
    display_in_card: bool = False,
) -> BuiltinFieldSpec:
    return BuiltinFieldSpec(
        internal_key=key,
        display_label=label,
        field_type=field_type,
        required=required,
        section=section,
        searchable=searchable,
        display_in_list=display_in_list,
        display_in_card=display_in_card,
    )


CHARACTER = BuiltinTypeSpec(
    type_key="character",
    display_name="Character",
    plural_display_name="Characters",
    description="A person (or person-like being) in the story.",
    icon_id="character",
    fields=(
        _f("full_name", "Full Name", FieldType.SHORT_TEXT, searchable=True),
        _f("aliases", "Aliases", FieldType.TAGS, searchable=True),
        _f("role", "Role", FieldType.SHORT_TEXT, display_in_list=True, display_in_card=True),
        _f("age", "Age", FieldType.SHORT_TEXT, display_in_card=True),
        _f("pronouns", "Pronouns", FieldType.SHORT_TEXT),
        _f("appearance", "Appearance", FieldType.LONG_TEXT, section="Profile"),
        _f("personality", "Personality", FieldType.LONG_TEXT, section="Profile"),
        _f("goals", "Goals", FieldType.LONG_TEXT, section="Story"),
        _f("motivation", "Motivation", FieldType.LONG_TEXT, section="Story"),
        _f("conflict", "Conflict", FieldType.LONG_TEXT, section="Story"),
        _f("backstory", "Backstory", FieldType.LONG_TEXT, section="Story"),
        _f("arc_notes", "Arc Notes", FieldType.LONG_TEXT, section="Story"),
        _f(
            "first_appearance", "First Appearance", FieldType.ENTITY_REFERENCE, section="Manuscript"
        ),
        _f("last_appearance", "Last Appearance", FieldType.ENTITY_REFERENCE, section="Manuscript"),
        _f("portrait_asset", "Portrait", FieldType.ASSET_REFERENCE, section="Profile"),
    ),
)

LOCATION = BuiltinTypeSpec(
    type_key="location",
    display_name="Location",
    plural_display_name="Locations",
    description="A place in the story's world.",
    icon_id="location",
    fields=(
        _f(
            "location_type",
            "Type",
            FieldType.SHORT_TEXT,
            display_in_list=True,
            display_in_card=True,
        ),
        _f("region", "Region", FieldType.SHORT_TEXT, searchable=True),
        _f("description", "Description", FieldType.LONG_TEXT, section="Profile"),
        _f("atmosphere", "Atmosphere", FieldType.LONG_TEXT, section="Profile"),
        _f("history", "History", FieldType.LONG_TEXT, section="Profile"),
        _f("population", "Population", FieldType.SHORT_TEXT, section="Profile"),
        _f("climate", "Climate", FieldType.SHORT_TEXT, section="Profile"),
        _f("scene_links", "Scene Links", FieldType.MULTI_ENTITY_REFERENCE, section="Manuscript"),
        _f("map_asset", "Map", FieldType.ASSET_REFERENCE, section="Profile"),
    ),
)

ORGANIZATION = BuiltinTypeSpec(
    type_key="organization",
    display_name="Organization",
    plural_display_name="Organizations",
    description="A group, faction, or institution.",
    icon_id="organization",
    fields=(
        _f("org_type", "Type", FieldType.SHORT_TEXT, display_in_list=True, display_in_card=True),
        _f("purpose", "Purpose", FieldType.LONG_TEXT, section="Profile"),
        _f("leadership", "Leadership", FieldType.MULTI_ENTITY_REFERENCE, section="Profile"),
        _f("members", "Members", FieldType.MULTI_ENTITY_REFERENCE, section="Profile"),
        _f("headquarters", "Headquarters", FieldType.ENTITY_REFERENCE, section="Profile"),
        _f("allies", "Allies", FieldType.MULTI_ENTITY_REFERENCE, section="Relations"),
        _f("rivals", "Rivals", FieldType.MULTI_ENTITY_REFERENCE, section="Relations"),
        _f("history", "History", FieldType.LONG_TEXT, section="Profile"),
    ),
)

ITEM = BuiltinTypeSpec(
    type_key="item",
    display_name="Item",
    plural_display_name="Items",
    description="An object of significance in the story.",
    icon_id="item",
    fields=(
        _f("item_type", "Type", FieldType.SHORT_TEXT, display_in_list=True, display_in_card=True),
        _f("owner", "Owner", FieldType.ENTITY_REFERENCE, section="Profile"),
        _f("description", "Description", FieldType.LONG_TEXT, section="Profile"),
        _f("origin", "Origin", FieldType.LONG_TEXT, section="Profile"),
        _f("significance", "Significance", FieldType.LONG_TEXT, section="Profile"),
        _f("abilities", "Abilities", FieldType.LONG_TEXT, section="Profile"),
        _f("limitations", "Limitations", FieldType.LONG_TEXT, section="Profile"),
    ),
)


def _minimal(
    type_key: str, display_name: str, plural: str, description: str, icon_id: str
) -> BuiltinTypeSpec:
    """A calm, minimal default for world-flavor types without an explicit
    field design in the spec: just enough to be useful, easy to grow later.
    """
    return BuiltinTypeSpec(
        type_key=type_key,
        display_name=display_name,
        plural_display_name=plural,
        description=description,
        icon_id=icon_id,
        fields=(
            _f("summary", "Summary", FieldType.LONG_TEXT, section="Profile", display_in_card=True),
            _f("notes", "Notes", FieldType.LONG_TEXT, section="Profile"),
        ),
    )


CULTURE = _minimal(
    "culture", "Culture", "Cultures", "A culture, custom, or way of life.", "culture"
)
SPECIES = _minimal(
    "species", "Species", "Species", "A species or race in the story's world.", "species"
)
MAGIC_SYSTEM = _minimal(
    "magic_system",
    "Magic System",
    "Magic Systems",
    "A system of magic and its rules.",
    "magic_system",
)
TECHNOLOGY = _minimal(
    "technology",
    "Technology",
    "Technologies",
    "A piece of technology or level of technological advancement.",
    "technology",
)
LANGUAGE = _minimal(
    "language", "Language", "Languages", "A language spoken in the story's world.", "language"
)
HISTORICAL_EVENT = _minimal(
    "historical_event",
    "Historical Event",
    "Historical Events",
    "An event from the story's history.",
    "event",
)
THEME = _minimal("theme", "Theme", "Themes", "A recurring theme or motif.", "theme")

ALL_BUILTIN_TYPES: tuple[BuiltinTypeSpec, ...] = (
    CHARACTER,
    LOCATION,
    ORGANIZATION,
    ITEM,
    CULTURE,
    SPECIES,
    MAGIC_SYSTEM,
    TECHNOLOGY,
    LANGUAGE,
    HISTORICAL_EVENT,
    THEME,
)
