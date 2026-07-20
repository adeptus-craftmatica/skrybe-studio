"""Field types and other small enums for the Story Bible's custom-field system."""

from __future__ import annotations

from enum import StrEnum


class FieldType(StrEnum):
    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    RICH_TEXT = "rich_text"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    CHOICE = "choice"
    MULTI_CHOICE = "multi_choice"
    ENTITY_REFERENCE = "entity_reference"
    MULTI_ENTITY_REFERENCE = "multi_entity_reference"
    ASSET_REFERENCE = "asset_reference"
    URL = "url"
    COLOR = "color"
    DURATION = "duration"
    NUMBER_WITH_UNIT = "number_with_unit"
    TAGS = "tags"


CHOICE_FIELD_TYPES = (FieldType.CHOICE, FieldType.MULTI_CHOICE)
"""Field types that read `FieldDefinition.choice_options`."""

REFERENCE_FIELD_TYPES = (
    FieldType.ENTITY_REFERENCE,
    FieldType.MULTI_ENTITY_REFERENCE,
    FieldType.ASSET_REFERENCE,
)
"""Field types whose stored value is one or more UUIDs, not a plain scalar."""

MULTI_VALUE_FIELD_TYPES = (
    FieldType.MULTI_CHOICE,
    FieldType.MULTI_ENTITY_REFERENCE,
    FieldType.TAGS,
)
"""Field types whose stored value is a list rather than a single scalar."""
