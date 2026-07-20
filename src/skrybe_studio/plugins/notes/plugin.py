"""The Notes plugin entrypoint: registration, activation, and lifecycle."""

from __future__ import annotations

import logging
from uuid import UUID

from skrybe_studio.core.contracts.command import Command
from skrybe_studio.core.plugins.base import Plugin
from skrybe_studio.core.plugins.context import PluginContext, ProjectContext
from skrybe_studio.core.workspaces.models import PanelPlacement, Workspace
from skrybe_studio.plugins.notes.application.search_provider import NotesSearchProvider
from skrybe_studio.plugins.notes.application.service import NotesService
from skrybe_studio.plugins.notes.domain.note import PLUGIN_ID
from skrybe_studio.plugins.notes.infrastructure.repository import NoteRepository
from skrybe_studio.plugins.notes.migrations import get_migrations
from skrybe_studio.plugins.notes.ui.browser_panel import NotesBrowserPanel
from skrybe_studio.plugins.notes.ui.editor_panel import NoteEditorPanel

logger = logging.getLogger(__name__)


class NotesPlugin(Plugin):
    """Reference plugin: plugin-owned persistence, entity creation, UI, commands, events, search."""

    def __init__(self) -> None:
        self._context: PluginContext | None = None
        self._search_provider: NotesSearchProvider | None = None
        self.service: NotesService | None = None
        self.selected_note_id: UUID | None = None

    def register(self, context: PluginContext) -> None:
        self._context = context

        context.panels.register(
            "notes.browser", "Notes", lambda: NotesBrowserPanel(self, context.events)
        )
        context.panels.register(
            "notes.editor", "Note Editor", lambda: NoteEditorPanel(self, context.events)
        )

        context.workspaces.register(
            Workspace(
                id="notes",
                title="Notes",
                central_panel_id="notes.editor",
                panels=(PanelPlacement(panel_id="notes.browser", area="left"),),
            )
        )

        context.commands.register(
            Command(
                id="notes.new_note",
                title="New Note",
                description="Create a new note in the current project.",
                shortcut="Ctrl+Shift+N",
                category="Notes",
                handler=self._create_note,
                is_enabled=lambda: self.service is not None,
            )
        )
        context.commands.register(
            Command(
                id="notes.delete_note",
                title="Delete Note",
                description="Delete the currently selected note.",
                category="Notes",
                handler=self._delete_selected_note,
                is_enabled=lambda: self.service is not None and self.selected_note_id is not None,
            )
        )
        logger.debug("Notes plugin registered")

    def activate(self, context: ProjectContext) -> None:
        repository = NoteRepository(context.database)
        context.migrations.apply(PLUGIN_ID, get_migrations())
        assert self._context is not None
        self.service = NotesService(repository, context.entities, self._context.events)
        self._search_provider = NotesSearchProvider(repository)
        self._context.search.register_provider(self._search_provider)
        logger.info("Notes plugin activated")

    def deactivate(self, context: ProjectContext) -> None:
        if self._context is not None and self._search_provider is not None:
            self._context.search.unregister_provider(self._search_provider)
        self._search_provider = None
        self.service = None
        self.selected_note_id = None
        logger.info("Notes plugin deactivated")

    def shutdown(self, context: PluginContext) -> None:
        logger.info("Notes plugin shut down")

    def set_selected_note(self, note_id: UUID | None) -> None:
        self.selected_note_id = note_id

    def _create_note(self) -> None:
        if self.service is not None:
            self.service.create_note("Untitled Note")

    def _delete_selected_note(self) -> None:
        if self.service is not None and self.selected_note_id is not None:
            self.service.delete_note(self.selected_note_id)
            self.selected_note_id = None
