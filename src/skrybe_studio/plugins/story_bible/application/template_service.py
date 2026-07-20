"""Manages entity templates - project-local, editable, removable data.

Built-in templates (see `domain/builtins.py`... note: built-in templates
are not yet seeded automatically; `seed_builtin_templates` does this
explicitly once, mirroring `SchemaService.seed_builtins_if_needed`) are
ordinary rows after seeding - editing or deleting one in a project never
mutates a "global" template, since no such global mutable state exists.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from skrybe_studio.plugins.story_bible.domain.models import EntityTemplate
from skrybe_studio.plugins.story_bible.infrastructure.repositories import TemplateRepository


class TemplateService:
    def __init__(self, templates: TemplateRepository) -> None:
        self._templates = templates

    def create_template(
        self,
        entity_type_id: UUID,
        name: str,
        field_values: dict[str, object] | None = None,
        *,
        is_builtin: bool = False,
    ) -> EntityTemplate:
        now = datetime.now(UTC)
        template = EntityTemplate(
            id=uuid4(),
            entity_type_id=entity_type_id,
            name=name,
            is_builtin=is_builtin,
            field_values=dict(field_values or {}),
            created_at=now,
            updated_at=now,
        )
        self._templates.add(template)
        return template

    def duplicate_template(
        self, template_id: UUID, *, new_name: str | None = None
    ) -> EntityTemplate | None:
        original = self._templates.get(template_id)
        if original is None:
            return None
        return self.create_template(
            original.entity_type_id,
            new_name or f"{original.name} Copy",
            dict(original.field_values),
        )

    def get_template(self, template_id: UUID) -> EntityTemplate | None:
        return self._templates.get(template_id)

    def list_templates(self, entity_type_id: UUID) -> list[EntityTemplate]:
        return self._templates.list_for_type(entity_type_id)

    def delete_template(self, template_id: UUID) -> bool:
        return self._templates.delete(template_id)
