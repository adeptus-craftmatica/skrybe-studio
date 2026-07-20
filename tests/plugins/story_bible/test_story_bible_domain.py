from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from skrybe_studio.plugins.story_bible.application.schema_service import slugify_type_key
from skrybe_studio.plugins.story_bible.domain.enums import FieldType
from skrybe_studio.plugins.story_bible.domain.exceptions import FieldValidationError
from skrybe_studio.plugins.story_bible.domain.models import FieldDefinition, entity_type_id_for
from skrybe_studio.plugins.story_bible.domain.validation import validate_value


def _field(
    field_type: FieldType, *, required: bool = False, choice_options: tuple[str, ...] = ()
) -> FieldDefinition:
    now = datetime.now(UTC)
    return FieldDefinition(
        id=uuid4(),
        entity_type_id=uuid4(),
        internal_key="test_field",
        display_label="Test Field",
        field_type=field_type,
        sort_order=1.0,
        required=required,
        choice_options=choice_options,
        created_at=now,
        updated_at=now,
    )


def test_entity_type_id_for_builds_the_namespaced_id() -> None:
    assert entity_type_id_for("character") == "story_bible.character"


def test_slugify_type_key_produces_a_machine_safe_key() -> None:
    assert slugify_type_key("Political Faction") == "political_faction"
    assert slugify_type_key("  Spaceship!  ") == "spaceship"


def test_required_field_rejects_missing_value() -> None:
    field = _field(FieldType.SHORT_TEXT, required=True)
    with pytest.raises(FieldValidationError):
        validate_value(field, None)


def test_optional_field_accepts_missing_value() -> None:
    field = _field(FieldType.SHORT_TEXT, required=False)
    validate_value(field, None)  # must not raise


def test_short_text_rejects_non_string() -> None:
    field = _field(FieldType.SHORT_TEXT)
    with pytest.raises(FieldValidationError):
        validate_value(field, 42)


def test_integer_rejects_float_and_bool() -> None:
    field = _field(FieldType.INTEGER)
    with pytest.raises(FieldValidationError):
        validate_value(field, 1.5)
    with pytest.raises(FieldValidationError):
        validate_value(field, True)
    validate_value(field, 5)  # must not raise


def test_decimal_accepts_int_and_float() -> None:
    field = _field(FieldType.DECIMAL)
    validate_value(field, 5)
    validate_value(field, 5.5)


def test_boolean_rejects_non_bool() -> None:
    field = _field(FieldType.BOOLEAN)
    with pytest.raises(FieldValidationError):
        validate_value(field, "true")
    validate_value(field, True)


def test_date_accepts_date_and_rejects_string() -> None:
    field = _field(FieldType.DATE)
    validate_value(field, date.today())
    with pytest.raises(FieldValidationError):
        validate_value(field, "2026-01-01")


def test_datetime_accepts_datetime() -> None:
    field = _field(FieldType.DATETIME)
    validate_value(field, datetime.now(UTC))


def test_choice_rejects_value_outside_options() -> None:
    field = _field(FieldType.CHOICE, choice_options=("draft", "final"))
    with pytest.raises(FieldValidationError):
        validate_value(field, "not-an-option")
    validate_value(field, "draft")


def test_multi_choice_rejects_any_unknown_option() -> None:
    field = _field(FieldType.MULTI_CHOICE, choice_options=("a", "b"))
    with pytest.raises(FieldValidationError):
        validate_value(field, ["a", "c"])
    validate_value(field, ["a", "b"])


def test_entity_reference_requires_a_uuid() -> None:
    field = _field(FieldType.ENTITY_REFERENCE)
    with pytest.raises(FieldValidationError):
        validate_value(field, "not-a-uuid")
    validate_value(field, uuid4())


def test_multi_entity_reference_requires_a_list_of_uuids() -> None:
    field = _field(FieldType.MULTI_ENTITY_REFERENCE)
    with pytest.raises(FieldValidationError):
        validate_value(field, [uuid4(), "nope"])
    validate_value(field, [uuid4(), uuid4()])


def test_tags_requires_a_list_of_strings() -> None:
    field = _field(FieldType.TAGS)
    with pytest.raises(FieldValidationError):
        validate_value(field, [1, 2])
    validate_value(field, ["a", "b"])


def test_number_with_unit_requires_amount_and_unit() -> None:
    field = _field(FieldType.NUMBER_WITH_UNIT)
    with pytest.raises(FieldValidationError):
        validate_value(field, {"amount": 5})
    with pytest.raises(FieldValidationError):
        validate_value(field, {"amount": "five", "unit": "km"})
    validate_value(field, {"amount": 5, "unit": "km"})


def test_duration_uses_the_same_shape_as_number_with_unit() -> None:
    field = _field(FieldType.DURATION)
    validate_value(field, {"amount": 3, "unit": "days"})
