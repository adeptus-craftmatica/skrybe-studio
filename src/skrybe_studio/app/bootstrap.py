"""The composition root: owns every core singleton and drives the plugin lifecycle.

Nothing here is manuscript-, timeline-, or story-bible-specific - this
module only wires generic core services together and hands plugins the
narrow contexts they are entitled to.
"""

from __future__ import annotations

import logging
from pathlib import Path

from skrybe_studio.app.paths import ApplicationPaths, resolve_application_paths
from skrybe_studio.core.commands.registry import CommandRegistry
from skrybe_studio.core.errors import install_excepthook
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.core.jobs.manager import JobManager
from skrybe_studio.core.logging_config import configure_logging
from skrybe_studio.core.plugins.context import PluginContext, ProjectContext
from skrybe_studio.core.plugins.loader import LoadedPlugin, PluginLoader, PluginLoadFailure
from skrybe_studio.core.projects.service import OpenProject, ProjectService
from skrybe_studio.core.search.service import SearchService
from skrybe_studio.core.services.container import ServiceContainer
from skrybe_studio.core.settings.service import SettingsService
from skrybe_studio.core.themes.manager import ThemeManager, ThemeMode
from skrybe_studio.core.workspaces.models import Workspace
from skrybe_studio.core.workspaces.panels import PanelRegistry
from skrybe_studio.core.workspaces.registry import WorkspaceRegistry

DEFAULT_WORKSPACE_ID = "default"

logger = logging.getLogger(__name__)


class Application:
    """Composition root shared by the desktop shell and the standalone plugin host."""

    def __init__(self, paths: ApplicationPaths | None = None) -> None:
        self.paths = paths or resolve_application_paths()
        configure_logging(self.paths.log_dir)
        install_excepthook()

        self.settings = SettingsService(self.paths.app_settings_file)
        self.events = EventBus()
        self.commands = CommandRegistry()
        self.workspaces = WorkspaceRegistry()
        self.workspaces.register(Workspace(id=DEFAULT_WORKSPACE_ID, title="Default"))
        self.panels = PanelRegistry()
        self.services = ServiceContainer()
        self.jobs = JobManager()
        self.search = SearchService()
        self.theme = ThemeManager(ThemeMode(self.settings.get_app("theme", ThemeMode.SYSTEM.value)))
        self.theme.theme_changed.connect(self._on_theme_changed)

        self.projects = ProjectService(self.settings)

        self._loader = PluginLoader([self.paths.builtin_plugins_dir])
        self._loaded_plugins: list[LoadedPlugin] = []
        self.plugin_failures: list[PluginLoadFailure] = []

        logger.info("Skrybe Studio application core initialized")

    def _on_theme_changed(self, _tokens: object) -> None:
        self.settings.set_app("theme", self.theme.mode.value)

    # --- plugin lifecycle ---------------------------------------------------

    def load_plugins(self) -> None:
        """Discover and register every plugin. Never raises - failures are collected."""
        result = self._loader.discover_and_instantiate()
        self.plugin_failures = list(result.failures)
        for loaded in result.loaded:
            context = self._build_plugin_context(loaded.manifest.id)
            try:
                loaded.instance.register(context)
            except Exception:
                logger.exception(
                    "Plugin '%s' raised during register(); it will not be activated",
                    loaded.manifest.id,
                )
                self.plugin_failures.append(
                    PluginLoadFailure(
                        plugin_id=loaded.manifest.id,
                        directory=loaded.directory,
                        category="register_error",
                        reason="Plugin raised an exception during register()",
                    )
                )
                continue
            self._loaded_plugins.append(loaded)
        logger.info(
            "Loaded %d plugin(s); %d failure(s)",
            len(self._loaded_plugins),
            len(self.plugin_failures),
        )

    @property
    def loaded_plugins(self) -> list[LoadedPlugin]:
        return list(self._loaded_plugins)

    def _build_plugin_context(self, plugin_id: str) -> PluginContext:
        return PluginContext(
            plugin_id=plugin_id,
            events=self.events,
            commands=self.commands,
            settings=self.settings,
            workspaces=self.workspaces,
            panels=self.panels,
            services=self.services,
            jobs=self.jobs,
            search=self.search,
        )

    def _build_project_context(self, plugin_id: str, project: OpenProject) -> ProjectContext:
        return ProjectContext(
            plugin_id=plugin_id,
            entities=project.entities,
            relationships=project.relationships,
            database=project.database,
            migrations=project.migrations,
        )

    # --- project lifecycle ---------------------------------------------------

    def create_project(self, root: Path, name: str) -> OpenProject:
        project = self.projects.create(root, name)
        self._activate_plugins(project)
        return project

    def open_project(self, root: Path) -> OpenProject:
        project = self.projects.open(root)
        self._activate_plugins(project)
        return project

    def close_project(self) -> None:
        project = self.projects.current
        if project is None:
            return
        for loaded in self._loaded_plugins:
            try:
                loaded.instance.deactivate(self._build_project_context(loaded.manifest.id, project))
            except Exception:
                logger.exception("Plugin '%s' raised during deactivate()", loaded.manifest.id)
        self.projects.close()

    def _activate_plugins(self, project: OpenProject) -> None:
        for loaded in self._loaded_plugins:
            try:
                loaded.instance.activate(self._build_project_context(loaded.manifest.id, project))
            except Exception:
                logger.exception("Plugin '%s' raised during activate()", loaded.manifest.id)

    def shutdown(self) -> None:
        self.close_project()
        for loaded in self._loaded_plugins:
            try:
                loaded.instance.shutdown(self._build_plugin_context(loaded.manifest.id))
            except Exception:
                logger.exception("Plugin '%s' raised during shutdown()", loaded.manifest.id)
        self.jobs.wait_for_done(2000)
        logger.info("Skrybe Studio application core shut down")
