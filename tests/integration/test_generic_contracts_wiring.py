"""Verifies the v0.3 generic core additions (entity/relationship type
registries, entity viewer registry, navigation service, issue service) are
actually constructed and threaded through `Application` into the contexts
plugins receive - no plugin uses them yet, so this is the only place that
exercises the wiring end to end.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from skrybe_studio.app.bootstrap import Application
from skrybe_studio.app.paths import ApplicationPaths
from skrybe_studio.core.contracts.navigation import NavigationTarget
from skrybe_studio.core.entities.relationship_type_registry import RelationshipTypeRegistry
from skrybe_studio.core.entities.type_registry import EntityTypeRegistry
from skrybe_studio.core.issues.service import IssueService
from skrybe_studio.core.navigation.service import NavigationService
from skrybe_studio.core.navigation.viewer_registry import EntityViewerRegistry


def test_application_constructs_the_app_wide_generic_services(
    app_paths: ApplicationPaths,
) -> None:
    app = Application(paths=app_paths)

    assert isinstance(app.entity_viewers, EntityViewerRegistry)
    assert isinstance(app.navigation, NavigationService)
    assert isinstance(app.issues, IssueService)

    app.shutdown()


def test_each_open_project_gets_its_own_type_registries(
    app_paths: ApplicationPaths, project_root: Path, tmp_path: Path
) -> None:
    app = Application(paths=app_paths)
    app.load_plugins()

    first = app.create_project(project_root, "First")
    assert isinstance(first.entity_types, EntityTypeRegistry)
    assert isinstance(first.relationship_types, RelationshipTypeRegistry)

    app.close_project()
    second_root = tmp_path / "Second.skrybe"
    second = app.create_project(second_root, "Second")

    assert second.entity_types is not first.entity_types
    assert second.relationship_types is not first.relationship_types

    app.close_project()
    app.shutdown()


def test_project_lifecycle_clears_cross_plugin_navigation_history(
    app_paths: ApplicationPaths, project_root: Path
) -> None:
    app = Application(paths=app_paths)
    app.load_plugins()
    app.create_project(project_root, "Nav Test")

    app.navigation.visit(NavigationTarget(entity_id=uuid4(), entity_type="story_bible.character"))
    assert app.navigation.current is not None

    app.close_project()

    assert app.navigation.current is None

    app.shutdown()
