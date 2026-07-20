"""Shared fixtures for Story Bible plugin tests - isolated tmp_path databases only."""

from __future__ import annotations

from pathlib import Path

import pytest

from skrybe_studio.core.entities.service import EntityService
from skrybe_studio.core.entities.type_registry import EntityTypeRegistry
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.core.storage.database import Database
from skrybe_studio.plugins.story_bible.application.entity_service import StoryBibleEntityService
from skrybe_studio.plugins.story_bible.application.schema_service import SchemaService
from skrybe_studio.plugins.story_bible.application.search_provider import StoryBibleSearchProvider
from skrybe_studio.plugins.story_bible.application.template_service import TemplateService
from skrybe_studio.plugins.story_bible.infrastructure.models import StoryBibleBase
from skrybe_studio.plugins.story_bible.infrastructure.repositories import (
    EntityTypeRepository,
    FieldDefinitionRepository,
    FieldValueRepository,
    StoryBibleEntityRepository,
    TemplateRepository,
)


@pytest.fixture
def story_bible_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "project.db")
    database.create_core_tables()
    StoryBibleBase.metadata.create_all(database.engine)
    return database


@pytest.fixture
def entity_type_repository(story_bible_database: Database) -> EntityTypeRepository:
    return EntityTypeRepository(story_bible_database)


@pytest.fixture
def field_definition_repository(story_bible_database: Database) -> FieldDefinitionRepository:
    return FieldDefinitionRepository(story_bible_database)


@pytest.fixture
def story_bible_entity_repository(story_bible_database: Database) -> StoryBibleEntityRepository:
    return StoryBibleEntityRepository(story_bible_database)


@pytest.fixture
def field_value_repository(story_bible_database: Database) -> FieldValueRepository:
    return FieldValueRepository(story_bible_database)


@pytest.fixture
def template_repository(story_bible_database: Database) -> TemplateRepository:
    return TemplateRepository(story_bible_database)


@pytest.fixture
def entities(story_bible_database: Database) -> EntityService:
    return EntityService(story_bible_database)


@pytest.fixture
def events() -> EventBus:
    return EventBus()


@pytest.fixture
def entity_type_registry() -> EntityTypeRegistry:
    return EntityTypeRegistry()


@pytest.fixture
def schema(
    entity_type_repository: EntityTypeRepository,
    field_definition_repository: FieldDefinitionRepository,
    entity_type_registry: EntityTypeRegistry,
    events: EventBus,
) -> SchemaService:
    return SchemaService(
        entity_type_repository, field_definition_repository, entity_type_registry, events
    )


@pytest.fixture
def story_bible_entities(
    story_bible_entity_repository: StoryBibleEntityRepository,
    field_value_repository: FieldValueRepository,
    schema: SchemaService,
    entities: EntityService,
    events: EventBus,
) -> StoryBibleEntityService:
    return StoryBibleEntityService(
        story_bible_entity_repository, field_value_repository, schema, entities, events
    )


@pytest.fixture
def templates(template_repository: TemplateRepository) -> TemplateService:
    return TemplateService(template_repository)


@pytest.fixture
def search_provider(
    story_bible_entities: StoryBibleEntityService, schema: SchemaService
) -> StoryBibleSearchProvider:
    return StoryBibleSearchProvider(story_bible_entities, schema)
