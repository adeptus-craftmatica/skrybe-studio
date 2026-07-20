"""The Asset Library plugin entrypoint: registration, activation, and lifecycle."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from PySide6.QtWidgets import QFileDialog

from skrybe_studio.core.contracts.command import Command
from skrybe_studio.core.plugins.base import Plugin
from skrybe_studio.core.plugins.context import PluginContext, ProjectContext
from skrybe_studio.core.workspaces.models import PanelPlacement, Workspace
from skrybe_studio.plugins.assets.application.search_provider import AssetsSearchProvider
from skrybe_studio.plugins.assets.application.service import AssetsService
from skrybe_studio.plugins.assets.domain.asset import PLUGIN_ID
from skrybe_studio.plugins.assets.infrastructure.repository import AssetRepository
from skrybe_studio.plugins.assets.migrations import get_migrations
from skrybe_studio.plugins.assets.ui.browser_panel import IMPORT_FILTER, AssetsBrowserPanel
from skrybe_studio.plugins.assets.ui.details_panel import AssetDetailsPanel

logger = logging.getLogger(__name__)


class AssetsPlugin(Plugin):
    """Reference plugin: project-local file management with background hashing/thumbnailing."""

    def __init__(self) -> None:
        self._context: PluginContext | None = None
        self._search_provider: AssetsSearchProvider | None = None
        self.service: AssetsService | None = None
        self.selected_asset_id: UUID | None = None

    def register(self, context: PluginContext) -> None:
        self._context = context

        context.panels.register(
            "assets.browser", "Asset Library", lambda: AssetsBrowserPanel(self, context.events)
        )
        context.panels.register(
            "assets.details", "Asset Details", lambda: AssetDetailsPanel(self, context.events)
        )

        context.workspaces.register(
            Workspace(
                id="assets",
                title="Assets",
                central_panel_id="assets.details",
                panels=(PanelPlacement(panel_id="assets.browser", area="left"),),
            )
        )

        context.commands.register(
            Command(
                id="assets.import_asset",
                title="Import Asset",
                description="Import a file into the project's managed asset library.",
                category="Assets",
                handler=self._import_asset,
                is_enabled=lambda: self.service is not None,
            )
        )
        context.commands.register(
            Command(
                id="assets.remove_asset",
                title="Remove Asset",
                description="Remove the currently selected asset from the project.",
                category="Assets",
                handler=self._remove_selected_asset,
                is_enabled=lambda: self.service is not None and self.selected_asset_id is not None,
            )
        )
        logger.debug("Assets plugin registered")

    def activate(self, context: ProjectContext) -> None:
        assert self._context is not None
        context.migrations.apply(PLUGIN_ID, get_migrations())
        repository = AssetRepository(context.database)
        project_root = context.database.path.parent
        assets_dir = project_root / "assets"
        cache_dir = project_root / "cache" / "thumbnails"
        self.service = AssetsService(
            repository,
            context.entities,
            self._context.events,
            self._context.jobs,
            assets_dir,
            cache_dir,
        )
        self._search_provider = AssetsSearchProvider(repository)
        self._context.search.register_provider(self._search_provider)
        logger.info("Assets plugin activated")

    def deactivate(self, context: ProjectContext) -> None:
        if self._context is not None and self._search_provider is not None:
            self._context.search.unregister_provider(self._search_provider)
        self._search_provider = None
        self.service = None
        self.selected_asset_id = None
        logger.info("Assets plugin deactivated")

    def shutdown(self, context: PluginContext) -> None:
        logger.info("Assets plugin shut down")

    def set_selected_asset(self, asset_id: UUID | None) -> None:
        self.selected_asset_id = asset_id

    def _import_asset(self) -> None:
        if self.service is None:
            return
        paths, _selected_filter = QFileDialog.getOpenFileNames(
            None, "Import Asset", "", IMPORT_FILTER
        )
        for path in paths:
            self.service.import_asset(Path(path))

    def _remove_selected_asset(self) -> None:
        if self.service is not None and self.selected_asset_id is not None:
            self.service.remove_asset(self.selected_asset_id)
            self.selected_asset_id = None
