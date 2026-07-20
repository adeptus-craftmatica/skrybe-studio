"""Shared fixtures for Manuscript plugin tests - isolated tmp_path databases only."""

from __future__ import annotations

from pathlib import Path

import pytest

from skrybe_studio.core.entities.service import EntityService
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.core.storage.database import Database
from skrybe_studio.plugins.manuscript.application.document_service import DocumentService
from skrybe_studio.plugins.manuscript.application.goals_service import GoalsService
from skrybe_studio.plugins.manuscript.application.hierarchy_service import HierarchyService
from skrybe_studio.plugins.manuscript.application.search_provider import ManuscriptSearchProvider
from skrybe_studio.plugins.manuscript.application.snapshot_service import SnapshotService
from skrybe_studio.plugins.manuscript.infrastructure.models import ManuscriptBase
from skrybe_studio.plugins.manuscript.infrastructure.repositories import (
    ManuscriptRepository,
    ProgressRepository,
    SnapshotRepository,
)


@pytest.fixture
def manuscript_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "project.db")
    database.create_core_tables()
    ManuscriptBase.metadata.create_all(database.engine)
    return database


@pytest.fixture
def manuscript_repository(manuscript_database: Database) -> ManuscriptRepository:
    return ManuscriptRepository(manuscript_database)


@pytest.fixture
def progress_repository(manuscript_database: Database) -> ProgressRepository:
    return ProgressRepository(manuscript_database)


@pytest.fixture
def snapshot_repository(manuscript_database: Database) -> SnapshotRepository:
    return SnapshotRepository(manuscript_database)


@pytest.fixture
def entities(manuscript_database: Database) -> EntityService:
    return EntityService(manuscript_database)


@pytest.fixture
def events() -> EventBus:
    return EventBus()


@pytest.fixture
def hierarchy(
    manuscript_repository: ManuscriptRepository, entities: EntityService, events: EventBus
) -> HierarchyService:
    return HierarchyService(manuscript_repository, entities, events)


@pytest.fixture
def documents(
    manuscript_repository: ManuscriptRepository,
    progress_repository: ProgressRepository,
    events: EventBus,
) -> DocumentService:
    return DocumentService(manuscript_repository, progress_repository, events)


@pytest.fixture
def snapshots(
    snapshot_repository: SnapshotRepository, documents: DocumentService, events: EventBus
) -> SnapshotService:
    return SnapshotService(snapshot_repository, documents, events)


@pytest.fixture
def goals(
    manuscript_repository: ManuscriptRepository, progress_repository: ProgressRepository
) -> GoalsService:
    return GoalsService(manuscript_repository, progress_repository)


@pytest.fixture
def search_provider(manuscript_repository: ManuscriptRepository) -> ManuscriptSearchProvider:
    return ManuscriptSearchProvider(manuscript_repository)
