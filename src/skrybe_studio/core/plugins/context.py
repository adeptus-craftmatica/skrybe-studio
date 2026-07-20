"""The narrow, stable interfaces plugins use to reach core services.

Plugins never receive the application object itself. Two distinct
contexts reflect when services actually become available:

- `PluginContext` is passed to `register()` and `shutdown()`: app-wide
  services that exist before any project is open (and outlive it).
- `ProjectContext` is passed to `activate()` and `deactivate()`:
  project-scoped services that only exist while a project is open.
"""

from __future__ import annotations

from dataclasses import dataclass

from skrybe_studio.core.commands.registry import CommandRegistry
from skrybe_studio.core.entities.relationship_type_registry import RelationshipTypeRegistry
from skrybe_studio.core.entities.relationships import RelationshipService
from skrybe_studio.core.entities.service import EntityService
from skrybe_studio.core.entities.type_registry import EntityTypeRegistry
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.core.issues.service import IssueService
from skrybe_studio.core.jobs.manager import JobManager
from skrybe_studio.core.navigation.service import NavigationService
from skrybe_studio.core.navigation.viewer_registry import EntityViewerRegistry
from skrybe_studio.core.search.service import SearchService
from skrybe_studio.core.services.container import ServiceContainer
from skrybe_studio.core.settings.service import SettingsService
from skrybe_studio.core.storage.database import Database
from skrybe_studio.core.storage.migration_coordinator import PluginMigrationCoordinator
from skrybe_studio.core.workspaces.panels import PanelRegistry
from skrybe_studio.core.workspaces.registry import WorkspaceRegistry


@dataclass(frozen=True, slots=True)
class PluginContext:
    """App-wide services, available at `register()` time and for the app's lifetime."""

    plugin_id: str
    events: EventBus
    commands: CommandRegistry
    settings: SettingsService
    workspaces: WorkspaceRegistry
    panels: PanelRegistry
    services: ServiceContainer
    jobs: JobManager
    search: SearchService
    entity_viewers: EntityViewerRegistry
    navigation: NavigationService
    issues: IssueService


@dataclass(frozen=True, slots=True)
class ProjectContext:
    """Project-scoped services, available only while a project is open."""

    plugin_id: str
    entities: EntityService
    relationships: RelationshipService
    database: Database
    migrations: PluginMigrationCoordinator
    entity_types: EntityTypeRegistry
    relationship_types: RelationshipTypeRegistry
