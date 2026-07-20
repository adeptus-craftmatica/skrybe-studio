"""Declarative field-value validation.

Every rule here is a plain type/shape check derived from the field's own
`FieldType` plus its `required`/`choice_options` settings - never arbitrary
executable validation code. Referential validity (does this UUID actually
point at a live entity/asset?) is deliberately **not** checked here - this
module is pure and DB-free; the application layer checks references
separately where a database connection exists.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from uuid import UUID

from skrybe_studio.plugins.story_bible.domain.enums import FieldType
from skrybe_studio.plugins.story_bible.domain.exceptions import FieldValidationError
from skrybe_studio.plugins.story_bible.domain.models import FieldDefinition

_Checker = Callable[[FieldDefinition, object], None]


def validate_value(definition: FieldDefinition, value: object | None) -> None:
    """Raises `FieldValidationError` if `value` is invalid for `definition`."""
    if value is None or value == () or value == [] or value == "":
        if definition.required:
            raise FieldValidationError(definition.internal_key, "this field is required")
        return

    checker = _CHECKERS.get(definition.field_type)
    if checker is not None:
        checker(definition, value)


def _check_text(definition: FieldDefinition, value: object) -> None:
    if not isinstance(value, str):
        raise FieldValidationError(definition.internal_key, "must be text")


def _check_boolean(definition: FieldDefinition, value: object) -> None:
    if not isinstance(value, bool):
        raise FieldValidationError(definition.internal_key, "must be true or false")


def _check_integer(definition: FieldDefinition, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise FieldValidationError(definition.internal_key, "must be a whole number")


def _check_decimal(definition: FieldDefinition, value: object) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise FieldValidationError(definition.internal_key, "must be a number")


def _check_date(definition: FieldDefinition, value: object) -> None:
    if not isinstance(value, date):
        raise FieldValidationError(definition.internal_key, "must be a date")


def _check_datetime(definition: FieldDefinition, value: object) -> None:
    if not isinstance(value, datetime):
        raise FieldValidationError(definition.internal_key, "must be a date and time")


def _check_choice(definition: FieldDefinition, value: object) -> None:
    if not isinstance(value, str) or value not in definition.choice_options:
        raise FieldValidationError(definition.internal_key, "must be one of the defined options")


def _check_multi_choice(definition: FieldDefinition, value: object) -> None:
    if not isinstance(value, list | tuple):
        raise FieldValidationError(definition.internal_key, "must be a list of options")
    invalid = [item for item in value if item not in definition.choice_options]
    if invalid:
        raise FieldValidationError(
            definition.internal_key, f"unknown options: {', '.join(map(str, invalid))}"
        )


def _check_entity_reference(definition: FieldDefinition, value: object) -> None:
    if not isinstance(value, UUID):
        raise FieldValidationError(definition.internal_key, "must reference a single entity")


def _check_multi_entity_reference(definition: FieldDefinition, value: object) -> None:
    if not isinstance(value, list | tuple) or not all(isinstance(v, UUID) for v in value):
        raise FieldValidationError(definition.internal_key, "must reference zero or more entities")


def _check_asset_reference(definition: FieldDefinition, value: object) -> None:
    if not isinstance(value, UUID):
        raise FieldValidationError(definition.internal_key, "must reference a single asset")


def _check_tags(definition: FieldDefinition, value: object) -> None:
    if not isinstance(value, list | tuple) or not all(isinstance(v, str) for v in value):
        raise FieldValidationError(definition.internal_key, "must be a list of tags")


def _check_magnitude_with_unit(definition: FieldDefinition, value: object) -> None:
    if not isinstance(value, dict) or "amount" not in value or "unit" not in value:
        raise FieldValidationError(
            definition.internal_key, 'must be an object like {"amount": 5, "unit": "days"}'
        )
    amount = value["amount"]
    if not isinstance(amount, int | float) or isinstance(amount, bool):
        raise FieldValidationError(definition.internal_key, "amount must be a number")
    if not isinstance(value["unit"], str):
        raise FieldValidationError(definition.internal_key, "unit must be text")


_CHECKERS: dict[FieldType, _Checker] = {
    FieldType.SHORT_TEXT: _check_text,
    FieldType.LONG_TEXT: _check_text,
    FieldType.RICH_TEXT: _check_text,
    FieldType.BOOLEAN: _check_boolean,
    FieldType.INTEGER: _check_integer,
    FieldType.DECIMAL: _check_decimal,
    FieldType.DATE: _check_date,
    FieldType.DATETIME: _check_datetime,
    FieldType.CHOICE: _check_choice,
    FieldType.MULTI_CHOICE: _check_multi_choice,
    FieldType.ENTITY_REFERENCE: _check_entity_reference,
    FieldType.MULTI_ENTITY_REFERENCE: _check_multi_entity_reference,
    FieldType.ASSET_REFERENCE: _check_asset_reference,
    FieldType.URL: _check_text,
    FieldType.COLOR: _check_text,
    FieldType.DURATION: _check_magnitude_with_unit,
    FieldType.NUMBER_WITH_UNIT: _check_magnitude_with_unit,
    FieldType.TAGS: _check_tags,
}
