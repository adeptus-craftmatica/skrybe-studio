"""Repositories over the Story Bible plugin's own tables."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import or_, select

from skrybe_studio.core.storage.database import Database
from skrybe_studio.plugins.story_bible.domain.enums import FieldType
from skrybe_studio.plugins.story_bible.domain.models import (
    EntityTemplate,
    EntityType,
    FieldDefinition,
    FieldValue,
    StoryBibleEntity,
)
from skrybe_studio.plugins.story_bible.infrastructure.models import (
    EntityTypeRecord,
    FieldDefinitionRecord,
    FieldValueRecord,
    StoryBibleEntityRecord,
    TemplateRecord,
)

_SORT_STEP = 1.0


def sort_order_between(before: float | None, after: float | None) -> float:
    """Fractional sort key between two siblings - reordering one row is a
    single-row update, never a bulk renumbering. Same algorithm the
    Manuscript plugin uses for its own binder ordering.
    """
    if before is None and after is None:
        return _SORT_STEP
    if before is None:
        return after - _SORT_STEP  # type: ignore[operator]
    if after is None:
        return before + _SORT_STEP
    return (before + after) / 2.0


# --- domain <-> record ---------------------------------------------------------------


def _type_to_domain(record: EntityTypeRecord) -> EntityType:
    return EntityType(
        id=record.id,
        type_key=record.type_key,
        is_builtin=record.is_builtin,
        display_name=record.display_name,
        plural_display_name=record.plural_display_name,
        description=record.description,
        icon_id=record.icon_id,
        color_token=record.color_token,
        user_instantiable=record.user_instantiable,
        user_extensible=record.user_extensible,
        user_archivable=record.user_archivable,
        created_at=record.created_at,
        updated_at=record.updated_at,
        archived_at=record.archived_at,
    )


def _field_to_domain(record: FieldDefinitionRecord) -> FieldDefinition:
    return FieldDefinition(
        id=record.id,
        entity_type_id=record.entity_type_id,
        internal_key=record.internal_key,
        display_label=record.display_label,
        field_type=FieldType(record.field_type),
        sort_order=record.sort_order,
        description=record.description,
        required=record.required,
        default_value=record.default_value_json,
        choice_options=tuple(record.choice_options_json or ()),
        section=record.section,
        searchable=record.searchable,
        display_in_list=record.display_in_list,
        display_in_card=record.display_in_card,
        active=record.active,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _entity_to_domain(record: StoryBibleEntityRecord) -> StoryBibleEntity:
    return StoryBibleEntity(
        id=record.id,
        entity_type_id=record.entity_type_id,
        primary_name=record.primary_name,
        summary=record.summary,
        aliases=tuple(record.aliases_json or ()),
        notes=record.notes,
        status=record.status,
        tags=tuple(record.tags_json or ()),
        created_at=record.created_at,
        updated_at=record.updated_at,
        archived_at=record.archived_at,
    )


def _template_to_domain(record: TemplateRecord) -> EntityTemplate:
    return EntityTemplate(
        id=record.id,
        entity_type_id=record.entity_type_id,
        name=record.name,
        is_builtin=record.is_builtin,
        field_values=dict(record.field_values_json or {}),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


# --- repositories ---------------------------------------------------------------------


class EntityTypeRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def add(self, entity_type: EntityType) -> None:
        with self._database.session() as session:
            session.add(
                EntityTypeRecord(
                    id=entity_type.id,
                    type_key=entity_type.type_key,
                    is_builtin=entity_type.is_builtin,
                    display_name=entity_type.display_name,
                    plural_display_name=entity_type.plural_display_name,
                    description=entity_type.description,
                    icon_id=entity_type.icon_id,
                    color_token=entity_type.color_token,
                    user_instantiable=entity_type.user_instantiable,
                    user_extensible=entity_type.user_extensible,
                    user_archivable=entity_type.user_archivable,
                    created_at=entity_type.created_at,
                    updated_at=entity_type.updated_at,
                    archived_at=entity_type.archived_at,
                )
            )

    def get(self, type_id: UUID) -> EntityType | None:
        with self._database.session() as session:
            record = session.get(EntityTypeRecord, type_id)
            return _type_to_domain(record) if record is not None else None

    def get_by_key(self, type_key: str) -> EntityType | None:
        with self._database.session() as session:
            stmt = select(EntityTypeRecord).where(EntityTypeRecord.type_key == type_key)
            record = session.scalars(stmt).first()
            return _type_to_domain(record) if record is not None else None

    def list(self, *, include_archived: bool = False) -> list[EntityType]:
        with self._database.session() as session:
            stmt = select(EntityTypeRecord).order_by(EntityTypeRecord.display_name)
            if not include_archived:
                stmt = stmt.where(EntityTypeRecord.archived_at.is_(None))
            return [_type_to_domain(record) for record in session.scalars(stmt)]

    def update(
        self,
        type_id: UUID,
        *,
        display_name: str | None = None,
        plural_display_name: str | None = None,
        description: str | None = None,
        icon_id: str | None = None,
        color_token: str | None = None,
    ) -> EntityType | None:
        with self._database.session() as session:
            record = session.get(EntityTypeRecord, type_id)
            if record is None:
                return None
            if display_name is not None:
                record.display_name = display_name
            if plural_display_name is not None:
                record.plural_display_name = plural_display_name
            if description is not None:
                record.description = description
            if icon_id is not None:
                record.icon_id = icon_id
            if color_token is not None:
                record.color_token = color_token
            record.updated_at = datetime.now(record.updated_at.tzinfo)
            session.flush()
            return _type_to_domain(record)

    def set_archived(self, type_id: UUID, archived_at: datetime | None) -> None:
        with self._database.session() as session:
            record = session.get(EntityTypeRecord, type_id)
            if record is not None:
                record.archived_at = archived_at


class FieldDefinitionRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def add(self, field_definition: FieldDefinition) -> None:
        with self._database.session() as session:
            session.add(
                FieldDefinitionRecord(
                    id=field_definition.id,
                    entity_type_id=field_definition.entity_type_id,
                    internal_key=field_definition.internal_key,
                    display_label=field_definition.display_label,
                    field_type=field_definition.field_type.value,
                    description=field_definition.description,
                    required=field_definition.required,
                    default_value_json=field_definition.default_value,
                    choice_options_json=list(field_definition.choice_options),
                    sort_order=field_definition.sort_order,
                    section=field_definition.section,
                    searchable=field_definition.searchable,
                    display_in_list=field_definition.display_in_list,
                    display_in_card=field_definition.display_in_card,
                    active=field_definition.active,
                    created_at=field_definition.created_at,
                    updated_at=field_definition.updated_at,
                )
            )

    def get(self, field_id: UUID) -> FieldDefinition | None:
        with self._database.session() as session:
            record = session.get(FieldDefinitionRecord, field_id)
            return _field_to_domain(record) if record is not None else None

    def list_for_type(
        self, entity_type_id: UUID, *, include_inactive: bool = False
    ) -> list[FieldDefinition]:
        with self._database.session() as session:
            stmt = (
                select(FieldDefinitionRecord)
                .where(FieldDefinitionRecord.entity_type_id == entity_type_id)
                .order_by(FieldDefinitionRecord.sort_order)
            )
            if not include_inactive:
                stmt = stmt.where(FieldDefinitionRecord.active.is_(True))
            return [_field_to_domain(record) for record in session.scalars(stmt)]

    def last_sort_order(self, entity_type_id: UUID) -> float | None:
        with self._database.session() as session:
            stmt = (
                select(FieldDefinitionRecord.sort_order)
                .where(FieldDefinitionRecord.entity_type_id == entity_type_id)
                .order_by(FieldDefinitionRecord.sort_order.desc())
                .limit(1)
            )
            return session.scalars(stmt).first()

    def update(
        self,
        field_id: UUID,
        *,
        display_label: str | None = None,
        description: str | None = None,
        required: bool | None = None,
        default_value: object | None = None,
        choice_options: tuple[str, ...] | None = None,
        section: str | None = None,
        searchable: bool | None = None,
        display_in_list: bool | None = None,
        display_in_card: bool | None = None,
        active: bool | None = None,
    ) -> FieldDefinition | None:
        with self._database.session() as session:
            record = session.get(FieldDefinitionRecord, field_id)
            if record is None:
                return None
            if display_label is not None:
                record.display_label = display_label
            if description is not None:
                record.description = description
            if required is not None:
                record.required = required
            if default_value is not None:
                record.default_value_json = default_value
            if choice_options is not None:
                record.choice_options_json = list(choice_options)
            if section is not None:
                record.section = section
            if searchable is not None:
                record.searchable = searchable
            if display_in_list is not None:
                record.display_in_list = display_in_list
            if display_in_card is not None:
                record.display_in_card = display_in_card
            if active is not None:
                record.active = active
            record.updated_at = datetime.now(record.updated_at.tzinfo)
            session.flush()
            return _field_to_domain(record)

    def set_sort_order(self, field_id: UUID, sort_order: float) -> None:
        with self._database.session() as session:
            record = session.get(FieldDefinitionRecord, field_id)
            if record is not None:
                record.sort_order = sort_order


class StoryBibleEntityRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def add(self, entity: StoryBibleEntity) -> None:
        with self._database.session() as session:
            session.add(
                StoryBibleEntityRecord(
                    id=entity.id,
                    entity_type_id=entity.entity_type_id,
                    primary_name=entity.primary_name,
                    summary=entity.summary,
                    aliases_json=list(entity.aliases),
                    notes=entity.notes,
                    status=entity.status,
                    tags_json=list(entity.tags),
                    created_at=entity.created_at,
                    updated_at=entity.updated_at,
                    archived_at=entity.archived_at,
                )
            )

    def get(self, entity_id: UUID) -> StoryBibleEntity | None:
        with self._database.session() as session:
            record = session.get(StoryBibleEntityRecord, entity_id)
            return _entity_to_domain(record) if record is not None else None

    def list(
        self,
        *,
        entity_type_id: UUID | None = None,
        include_archived: bool = False,
    ) -> list[StoryBibleEntity]:
        with self._database.session() as session:
            stmt = select(StoryBibleEntityRecord).order_by(StoryBibleEntityRecord.primary_name)
            if entity_type_id is not None:
                stmt = stmt.where(StoryBibleEntityRecord.entity_type_id == entity_type_id)
            if not include_archived:
                stmt = stmt.where(StoryBibleEntityRecord.archived_at.is_(None))
            return [_entity_to_domain(record) for record in session.scalars(stmt)]

    def update(
        self,
        entity_id: UUID,
        *,
        primary_name: str | None = None,
        summary: str | None = None,
        aliases: tuple[str, ...] | None = None,
        notes: str | None = None,
        status: str | None = None,
        tags: tuple[str, ...] | None = None,
    ) -> StoryBibleEntity | None:
        with self._database.session() as session:
            record = session.get(StoryBibleEntityRecord, entity_id)
            if record is None:
                return None
            if primary_name is not None:
                record.primary_name = primary_name
            if summary is not None:
                record.summary = summary
            if aliases is not None:
                record.aliases_json = list(aliases)
            if notes is not None:
                record.notes = notes
            if status is not None:
                record.status = status
            if tags is not None:
                record.tags_json = list(tags)
            record.updated_at = datetime.now(record.updated_at.tzinfo)
            session.flush()
            return _entity_to_domain(record)

    def set_archived(self, entity_id: UUID, archived_at: datetime | None) -> None:
        with self._database.session() as session:
            record = session.get(StoryBibleEntityRecord, entity_id)
            if record is not None:
                record.archived_at = archived_at

    def set_entity_type(self, entity_id: UUID, entity_type_id: UUID) -> StoryBibleEntity | None:
        with self._database.session() as session:
            record = session.get(StoryBibleEntityRecord, entity_id)
            if record is None:
                return None
            record.entity_type_id = entity_type_id
            record.updated_at = datetime.now(record.updated_at.tzinfo)
            session.flush()
            return _entity_to_domain(record)

    def search(self, query: str) -> list[StoryBibleEntity]:
        needle = f"%{query.lower()}%"
        with self._database.session() as session:
            stmt = select(StoryBibleEntityRecord).where(
                StoryBibleEntityRecord.archived_at.is_(None),
                or_(
                    StoryBibleEntityRecord.primary_name.ilike(needle),
                    StoryBibleEntityRecord.summary.ilike(needle),
                ),
            )
            matches = [_entity_to_domain(record) for record in session.scalars(stmt)]
        alias_matches = [
            entity
            for entity in self.list()
            if any(query.lower() in alias.lower() for alias in entity.aliases)
            and entity.id not in {m.id for m in matches}
        ]
        return matches + alias_matches


class FieldValueRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get_for_entity(self, entity_id: UUID) -> dict[UUID, object | None]:
        with self._database.session() as session:
            stmt = select(FieldValueRecord).where(FieldValueRecord.entity_id == entity_id)
            return {
                record.field_definition_id: record.value_json for record in session.scalars(stmt)
            }

    def set(self, entity_id: UUID, field_definition_id: UUID, value: object | None) -> FieldValue:
        with self._database.session() as session:
            stmt = select(FieldValueRecord).where(
                FieldValueRecord.entity_id == entity_id,
                FieldValueRecord.field_definition_id == field_definition_id,
            )
            record = session.scalars(stmt).first()
            if record is None:
                record = FieldValueRecord(
                    id=uuid4(),
                    entity_id=entity_id,
                    field_definition_id=field_definition_id,
                    value_json=value,
                )
                session.add(record)
            else:
                record.value_json = value
            session.flush()
            return FieldValue(
                id=record.id,
                entity_id=entity_id,
                field_definition_id=field_definition_id,
                value=value,
            )


class TemplateRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def add(self, template: EntityTemplate) -> None:
        with self._database.session() as session:
            session.add(
                TemplateRecord(
                    id=template.id,
                    entity_type_id=template.entity_type_id,
                    name=template.name,
                    is_builtin=template.is_builtin,
                    field_values_json=dict(template.field_values),
                    created_at=template.created_at,
                    updated_at=template.updated_at,
                )
            )

    def get(self, template_id: UUID) -> EntityTemplate | None:
        with self._database.session() as session:
            record = session.get(TemplateRecord, template_id)
            return _template_to_domain(record) if record is not None else None

    def list_for_type(self, entity_type_id: UUID) -> list[EntityTemplate]:
        with self._database.session() as session:
            stmt = (
                select(TemplateRecord)
                .where(TemplateRecord.entity_type_id == entity_type_id)
                .order_by(TemplateRecord.name)
            )
            return [_template_to_domain(record) for record in session.scalars(stmt)]

    def delete(self, template_id: UUID) -> bool:
        with self._database.session() as session:
            record = session.get(TemplateRecord, template_id)
            if record is None:
                return False
            session.delete(record)
            return True
