"""Create, open, close, and validate `.skrybe` project directories."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from skrybe_studio.core.entities.relationship_type_registry import RelationshipTypeRegistry
from skrybe_studio.core.entities.relationships import RelationshipService
from skrybe_studio.core.entities.service import EntityService
from skrybe_studio.core.entities.type_registry import EntityTypeRegistry
from skrybe_studio.core.projects.errors import (
    InvalidProjectError,
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
)
from skrybe_studio.core.projects.models import ProjectMetadata
from skrybe_studio.core.projects.paths import PROJECT_SUFFIX, ProjectPaths
from skrybe_studio.core.projects.recent import RecentProjectsStore
from skrybe_studio.core.settings.service import SettingsService
from skrybe_studio.core.storage.database import Database
from skrybe_studio.core.storage.migration_coordinator import PluginMigrationCoordinator

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OpenProject:
    """The narrow, read-mostly view of the open project exposed to the rest of the app."""

    metadata: ProjectMetadata
    paths: ProjectPaths
    database: Database
    entities: EntityService
    relationships: RelationshipService
    migrations: PluginMigrationCoordinator
    entity_types: EntityTypeRegistry
    relationship_types: RelationshipTypeRegistry


class ProjectService:
    """Owns the lifecycle of at most one open `.skrybe` project at a time."""

    def __init__(self, settings: SettingsService) -> None:
        self._settings = settings
        self._recent = RecentProjectsStore(settings)
        self._current: OpenProject | None = None

    @property
    def current(self) -> OpenProject | None:
        return self._current

    @property
    def recent_projects(self) -> RecentProjectsStore:
        return self._recent

    def create(self, root: Path, name: str) -> OpenProject:
        if not root.name.endswith(PROJECT_SUFFIX):
            root = root.with_name(root.name + PROJECT_SUFFIX)
        if root.exists() and any(root.iterdir()):
            raise ProjectAlreadyExistsError(f"'{root}' already exists and is not empty")

        paths = ProjectPaths(root=root)
        root.mkdir(parents=True, exist_ok=True)
        for directory in paths.all_directories():
            directory.mkdir(parents=True, exist_ok=True)

        now = datetime.now(UTC)
        metadata = ProjectMetadata(id=uuid4(), name=name, created_at=now, updated_at=now)
        paths.metadata_file.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")

        logger.info("Created project '%s' at %s", name, root)
        return self._open_paths(paths)

    def open(self, root: Path) -> OpenProject:
        paths = ProjectPaths(root=root)
        self.validate(paths)
        opened = self._open_paths(paths)
        logger.info("Opened project '%s' from %s", opened.metadata.name, root)
        return opened

    def close(self) -> None:
        if self._current is None:
            return
        logger.info("Closing project '%s'", self._current.metadata.name)
        self._current.database.dispose()
        self._settings.detach_project()
        self._current = None

    def validate(self, paths: ProjectPaths) -> None:
        if not paths.root.is_dir():
            raise ProjectNotFoundError(f"'{paths.root}' does not exist")
        if not paths.metadata_file.exists():
            raise InvalidProjectError(f"'{paths.root}' is missing project.json")
        try:
            raw = json.loads(paths.metadata_file.read_text(encoding="utf-8"))
            ProjectMetadata.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise InvalidProjectError(f"'{paths.root}' has an invalid project.json: {exc}") from exc

    def _open_paths(self, paths: ProjectPaths) -> OpenProject:
        metadata = ProjectMetadata.model_validate_json(
            paths.metadata_file.read_text(encoding="utf-8")
        )
        database = Database(paths.database_file)
        database.create_core_tables()
        entities = EntityService(database)
        relationships = RelationshipService(database)
        migrations = PluginMigrationCoordinator(database)
        self._settings.attach_project(paths.settings_file)

        project = OpenProject(
            metadata=metadata,
            paths=paths,
            database=database,
            entities=entities,
            relationships=relationships,
            migrations=migrations,
            entity_types=EntityTypeRegistry(),
            relationship_types=RelationshipTypeRegistry(),
        )
        self._current = project
        self._recent.record_opened(paths.root, metadata.name)
        return project
