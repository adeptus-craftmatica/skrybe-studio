from __future__ import annotations

from uuid import uuid4

from skrybe_studio.plugins.story_bible.application.schema_service import SchemaService
from skrybe_studio.plugins.story_bible.application.template_service import TemplateService


def test_create_template_stores_field_values(
    schema: SchemaService, templates: TemplateService
) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")

    template = templates.create_template(entity_type.id, "Cruiser Preset", {"class": "Cruiser"})

    assert template.field_values == {"class": "Cruiser"}
    assert [t.id for t in templates.list_templates(entity_type.id)] == [template.id]


def test_duplicate_template_copies_field_values(
    schema: SchemaService, templates: TemplateService
) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    original = templates.create_template(entity_type.id, "Cruiser Preset", {"class": "Cruiser"})

    duplicate = templates.duplicate_template(original.id)

    assert duplicate is not None
    assert duplicate.name == "Cruiser Preset Copy"
    assert duplicate.field_values == {"class": "Cruiser"}
    assert duplicate.id != original.id


def test_delete_template_removes_it(schema: SchemaService, templates: TemplateService) -> None:
    entity_type = schema.create_custom_type("Spaceship", "Spaceships")
    template = templates.create_template(entity_type.id, "Cruiser Preset")

    assert templates.delete_template(template.id) is True

    assert templates.list_templates(entity_type.id) == []


def test_delete_unknown_template_returns_false(templates: TemplateService) -> None:
    assert templates.delete_template(uuid4()) is False
