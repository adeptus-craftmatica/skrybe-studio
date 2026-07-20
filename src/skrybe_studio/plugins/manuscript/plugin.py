"""The Manuscript plugin entrypoint: registration, activation, commands, and lifecycle."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from PySide6.QtWidgets import QDockWidget, QFileDialog, QMessageBox

from skrybe_studio.core.contracts.command import Command
from skrybe_studio.core.plugins.base import Plugin
from skrybe_studio.core.plugins.context import PluginContext, ProjectContext
from skrybe_studio.core.workspaces.models import PanelPlacement, Workspace
from skrybe_studio.plugins.manuscript.application.asset_integration import ManuscriptAssetService
from skrybe_studio.plugins.manuscript.application.document_service import DocumentService
from skrybe_studio.plugins.manuscript.application.export.compile import Compiler
from skrybe_studio.plugins.manuscript.application.export.service import (
    EXPORT_FORMAT_EXTENSIONS,
    ExportService,
)
from skrybe_studio.plugins.manuscript.application.goals_service import GoalsService
from skrybe_studio.plugins.manuscript.application.hierarchy_service import HierarchyService
from skrybe_studio.plugins.manuscript.application.navigation import NavigationHistory
from skrybe_studio.plugins.manuscript.application.search_provider import ManuscriptSearchProvider
from skrybe_studio.plugins.manuscript.application.snapshot_service import SnapshotService
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType
from skrybe_studio.plugins.manuscript.domain.exceptions import ManuscriptError
from skrybe_studio.plugins.manuscript.domain.models import PLUGIN_ID
from skrybe_studio.plugins.manuscript.infrastructure.repositories import (
    ManuscriptRepository,
    ProgressRepository,
    SnapshotRepository,
)
from skrybe_studio.plugins.manuscript.migrations import get_migrations
from skrybe_studio.plugins.manuscript.ui.binder.panel import BinderPanel
from skrybe_studio.plugins.manuscript.ui.dialogs.export_dialog import ExportDialog
from skrybe_studio.plugins.manuscript.ui.dialogs.new_manuscript_dialog import NewManuscriptDialog
from skrybe_studio.plugins.manuscript.ui.dialogs.snapshots_dialog import SnapshotsDialog
from skrybe_studio.plugins.manuscript.ui.editor.editor_panel import EditorPanel
from skrybe_studio.plugins.manuscript.ui.inspector.panel import InspectorPanel
from skrybe_studio.plugins.manuscript.ui.search_panel import ManuscriptSearchPanel

logger = logging.getLogger(__name__)

_POINT_SIZE_KEY = "editor.point_size"
_TYPEWRITER_KEY = "editor.typewriter_enabled"
_OPEN_TABS_KEY = "editor.open_tabs"
_DEFAULT_POINT_SIZE = 13.0


class ManuscriptPlugin(Plugin):
    """Binder-organized manuscript writing: hierarchy, editor, snapshots, search, export."""

    def __init__(self) -> None:
        self._context: PluginContext | None = None
        self._search_provider_registered = False

        self.hierarchy: HierarchyService | None = None
        self.documents: DocumentService | None = None
        self.snapshots: SnapshotService | None = None
        self.goals: GoalsService | None = None
        self.assets: ManuscriptAssetService | None = None
        self.search_provider: ManuscriptSearchProvider | None = None
        self._export_service: ExportService | None = None
        self.navigation = NavigationHistory()
        self.suppress_navigation_recording = False

        self.selected_node_id: UUID | None = None
        self._binder_panel: BinderPanel | None = None
        self._editor_panel: EditorPanel | None = None

    # --- lifecycle -----------------------------------------------------------------

    def register(self, context: PluginContext) -> None:
        self._context = context

        context.panels.register(
            "manuscript.binder", "Binder", lambda: BinderPanel(self, context.events)
        )
        context.panels.register(
            "manuscript.editor", "Editor", lambda: EditorPanel(self, context.events)
        )
        context.panels.register(
            "manuscript.inspector", "Inspector", lambda: InspectorPanel(self, context.events)
        )
        context.panels.register(
            "manuscript.search", "Manuscript Search", lambda: ManuscriptSearchPanel(self)
        )

        context.workspaces.register(
            Workspace(
                id="manuscript",
                title="Writing",
                central_panel_id="manuscript.editor",
                panels=(
                    PanelPlacement(panel_id="manuscript.binder", area="left"),
                    PanelPlacement(panel_id="manuscript.inspector", area="right"),
                    PanelPlacement(panel_id="manuscript.search", area="bottom"),
                ),
            )
        )

        self._register_commands(context)
        logger.debug("Manuscript plugin registered")

    def _register_commands(self, context: PluginContext) -> None:
        def register(
            command_id: str,
            title: str,
            handler,
            *,
            shortcut: str | None = None,
            category: str = "Manuscript",
            enabled=None,
        ) -> None:
            context.commands.register(
                Command(
                    id=command_id,
                    title=title,
                    handler=handler,
                    shortcut=shortcut,
                    category=category,
                    is_enabled=enabled or (lambda: self.hierarchy is not None),
                )
            )

        has_selection = lambda: self.hierarchy is not None and self.selected_node_id is not None  # noqa: E731

        register(
            "manuscript.new_manuscript",
            "New Manuscript",
            self._cmd_new_manuscript,
            shortcut="Ctrl+Shift+M",
        )
        register(
            "manuscript.new_folder",
            "New Folder",
            lambda: self._cmd_new_node(ManuscriptNodeType.FOLDER),
        )
        register(
            "manuscript.new_part", "New Part", lambda: self._cmd_new_node(ManuscriptNodeType.PART)
        )
        register(
            "manuscript.new_chapter",
            "New Chapter",
            lambda: self._cmd_new_node(ManuscriptNodeType.CHAPTER),
        )
        register(
            "manuscript.new_scene",
            "New Scene",
            lambda: self._cmd_new_node(ManuscriptNodeType.SCENE),
            shortcut="Ctrl+Shift+S",
        )
        register(
            "manuscript.new_document",
            "New Document",
            lambda: self._cmd_new_node(ManuscriptNodeType.DOCUMENT),
        )
        register(
            "manuscript.rename_node", "Rename Node", self._cmd_rename_node, enabled=has_selection
        )
        register(
            "manuscript.duplicate_node",
            "Duplicate Node",
            self._cmd_duplicate_node,
            enabled=has_selection,
        )
        register(
            "manuscript.archive_node", "Archive Node", self._cmd_archive_node, enabled=has_selection
        )
        register(
            "manuscript.move_node_up",
            "Move Node Up",
            lambda: self._cmd_move_sibling(-1),
            enabled=has_selection,
        )
        register(
            "manuscript.move_node_down",
            "Move Node Down",
            lambda: self._cmd_move_sibling(1),
            enabled=has_selection,
        )
        register(
            "manuscript.focus_editor", "Focus Editor", self._cmd_focus_editor, enabled=has_selection
        )
        register(
            "manuscript.toggle_inspector",
            "Toggle Inspector",
            self._cmd_toggle_inspector,
            enabled=lambda: True,
        )
        register(
            "manuscript.toggle_focus_mode",
            "Toggle Focus Mode",
            self._cmd_toggle_focus_mode,
            shortcut="Ctrl+Shift+F",
            enabled=lambda: True,
        )
        register(
            "manuscript.toggle_typewriter",
            "Toggle Typewriter Scrolling",
            self._cmd_toggle_typewriter,
            enabled=lambda: True,
        )
        register("manuscript.find", "Find", self._cmd_find, shortcut="Ctrl+F", enabled=lambda: True)
        register("manuscript.replace", "Replace", self._cmd_find, enabled=lambda: True)
        register(
            "manuscript.search_manuscript",
            "Search Manuscript",
            self._cmd_search_manuscript,
            enabled=lambda: True,
        )
        register(
            "manuscript.create_snapshot",
            "Create Snapshot",
            self._cmd_create_snapshot,
            enabled=has_selection,
        )
        register(
            "manuscript.show_snapshots",
            "Show Snapshots",
            self._cmd_show_snapshots,
            enabled=has_selection,
        )
        register(
            "manuscript.compile",
            "Compile Manuscript",
            self._cmd_compile,
            shortcut="Ctrl+Shift+E",
        )
        register(
            "manuscript.navigate_back",
            "Navigate Back",
            self._cmd_navigate_back,
            enabled=lambda: self.navigation.can_go_back,
        )
        register(
            "manuscript.navigate_forward",
            "Navigate Forward",
            self._cmd_navigate_forward,
            enabled=lambda: self.navigation.can_go_forward,
        )
        register(
            "manuscript.reveal_in_binder",
            "Reveal in Binder",
            self._cmd_reveal_in_binder,
            enabled=has_selection,
        )
        register(
            "manuscript.toggle_split",
            "Toggle Split Editor",
            self._cmd_toggle_split,
            enabled=lambda: True,
        )

    def activate(self, context: ProjectContext) -> None:
        assert self._context is not None
        context.migrations.apply(PLUGIN_ID, get_migrations())
        repository = ManuscriptRepository(context.database)
        snapshot_repository = SnapshotRepository(context.database)
        progress_repository = ProgressRepository(context.database)

        self.hierarchy = HierarchyService(repository, context.entities, self._context.events)
        self.documents = DocumentService(repository, progress_repository, self._context.events)
        self.snapshots = SnapshotService(snapshot_repository, self.documents, self._context.events)
        self.goals = GoalsService(repository, progress_repository)
        self.assets = ManuscriptAssetService(context.relationships, self._context.services)
        self.search_provider = ManuscriptSearchProvider(repository)
        self._export_service = ExportService(Compiler(repository), self._context.jobs)
        self.navigation = NavigationHistory()

        self._context.search.register_provider(self.search_provider)
        self._search_provider_registered = True
        logger.info("Manuscript plugin activated")

    def deactivate(self, context: ProjectContext) -> None:
        self._flush_editor_safely()
        if (
            self._context is not None
            and self._search_provider_registered
            and self.search_provider is not None
        ):
            self._context.search.unregister_provider(self.search_provider)
        self._search_provider_registered = False
        self.hierarchy = None
        self.documents = None
        self.snapshots = None
        self.goals = None
        self.assets = None
        self.search_provider = None
        self._export_service = None
        self.selected_node_id = None
        self._binder_panel = None
        self._editor_panel = None
        logger.info("Manuscript plugin deactivated")

    def shutdown(self, context: PluginContext) -> None:
        self._flush_editor_safely()
        logger.info("Manuscript plugin shut down")

    def _flush_editor_safely(self) -> None:
        if self._editor_panel is None:
            return
        try:
            self._editor_panel.flush_all()
        except RuntimeError:
            logger.debug("Editor panel was already deleted; nothing to flush")

    # --- panel-facing helpers --------------------------------------------------------

    def set_selected_node(self, node_id: UUID | None) -> None:
        self.selected_node_id = node_id

    def set_binder_panel(self, panel: BinderPanel) -> None:
        self._binder_panel = panel

    def set_editor_panel(self, panel: EditorPanel) -> None:
        self._editor_panel = panel

    def reveal_and_open(self, node_id: UUID, *, record_navigation: bool = True) -> None:
        previous = self.suppress_navigation_recording
        self.suppress_navigation_recording = not record_navigation
        try:
            self.set_selected_node(node_id)
            if self._binder_panel is not None:
                try:
                    self._binder_panel.reveal_node(node_id)
                except RuntimeError:
                    self._binder_panel = None
            if self._editor_panel is not None and self.hierarchy is not None:
                node = self.hierarchy.get_node(node_id)
                if node is not None and node.is_text_bearing:
                    try:
                        self._editor_panel.open_document(node_id)
                    except RuntimeError:
                        self._editor_panel = None
        finally:
            self.suppress_navigation_recording = previous

    # --- settings-backed editor preferences (project-scoped) --------------------------

    def get_editor_point_size(self) -> float:
        if self._context is None:
            return _DEFAULT_POINT_SIZE
        return float(
            self._context.settings.get_plugin(
                PLUGIN_ID, _POINT_SIZE_KEY, _DEFAULT_POINT_SIZE, project_scope=True
            )
        )

    def set_editor_point_size(self, value: float) -> None:
        if self._context is not None:
            self._context.settings.set_plugin(PLUGIN_ID, _POINT_SIZE_KEY, value, project_scope=True)

    def get_typewriter_enabled(self) -> bool:
        if self._context is None:
            return False
        return bool(
            self._context.settings.get_plugin(PLUGIN_ID, _TYPEWRITER_KEY, False, project_scope=True)
        )

    def set_typewriter_enabled(self, enabled: bool) -> None:
        if self._context is not None:
            self._context.settings.set_plugin(
                PLUGIN_ID, _TYPEWRITER_KEY, enabled, project_scope=True
            )
        if self._editor_panel is not None:
            self._editor_panel.set_typewriter_enabled(enabled)

    def get_open_tab_ids(self) -> list[str]:
        if self._context is None:
            return []
        return list(
            self._context.settings.get_plugin(PLUGIN_ID, _OPEN_TABS_KEY, [], project_scope=True)
        )

    def set_open_tab_ids(self, ids: list[str]) -> None:
        if self._context is not None:
            self._context.settings.set_plugin(PLUGIN_ID, _OPEN_TABS_KEY, ids, project_scope=True)

    # --- command handlers ------------------------------------------------------------

    def _cmd_new_manuscript(self) -> None:
        dialog = NewManuscriptDialog()
        if dialog.exec() == NewManuscriptDialog.DialogCode.Accepted and self.hierarchy is not None:
            self.hierarchy.create_manuscript(dialog.title(), dialog.template())

    def _cmd_new_node(self, node_type: ManuscriptNodeType) -> None:
        if self.hierarchy is None:
            return
        parent_id = self.selected_node_id
        if parent_id is None:
            manuscripts = self.hierarchy.list_manuscripts()
            if not manuscripts:
                return
            parent_id = manuscripts[0].id
        try:
            self.hierarchy.create_node(parent_id, node_type, f"New {node_type.value.title()}")
        except ManuscriptError as exc:
            logger.warning("Could not create node: %s", exc)

    def _cmd_rename_node(self) -> None:
        if self._binder_panel is not None:
            try:
                self._binder_panel.start_rename_selected()
            except RuntimeError:
                self._binder_panel = None

    def _cmd_duplicate_node(self) -> None:
        if self.hierarchy is not None and self.selected_node_id is not None:
            self.hierarchy.duplicate_node(self.selected_node_id)

    def _cmd_archive_node(self) -> None:
        if self.hierarchy is not None and self.selected_node_id is not None:
            self.hierarchy.archive_node(self.selected_node_id)

    def _cmd_move_sibling(self, direction: int) -> None:
        if self.hierarchy is not None and self.selected_node_id is not None:
            self.hierarchy.move_sibling(self.selected_node_id, direction=direction)

    def _cmd_focus_editor(self) -> None:
        if self.selected_node_id is not None:
            self.reveal_and_open(self.selected_node_id)

    def _cmd_toggle_inspector(self) -> None:
        self._toggle_dock("dock.manuscript.inspector")

    def _cmd_search_manuscript(self) -> None:
        if self._editor_panel is None:
            return
        dock = self._editor_panel.window().findChild(QDockWidget, "dock.manuscript.search")
        if dock is not None:
            dock.setVisible(True)
            dock.raise_()

    def _toggle_dock(self, object_name: str) -> None:
        if self._editor_panel is None:
            return
        dock = self._editor_panel.window().findChild(QDockWidget, object_name)
        if dock is not None:
            dock.setVisible(not dock.isVisible())

    def _cmd_toggle_focus_mode(self) -> None:
        if self._editor_panel is not None:
            self._editor_panel.toggle_focus_mode()

    def _cmd_toggle_typewriter(self) -> None:
        self.set_typewriter_enabled(not self.get_typewriter_enabled())

    def _cmd_find(self) -> None:
        if self._editor_panel is not None:
            self._editor_panel.show_find_bar()

    def _cmd_create_snapshot(self) -> None:
        if self.snapshots is not None and self.selected_node_id is not None:
            self.snapshots.create_snapshot(self.selected_node_id)

    def _cmd_show_snapshots(self) -> None:
        if self.selected_node_id is not None:
            SnapshotsDialog(self, self.selected_node_id).exec()

    def _cmd_compile(self) -> None:
        if self.hierarchy is None or self._export_service is None:
            return
        manuscript_id = self._resolve_current_manuscript_id()
        if manuscript_id is None:
            return

        dialog = ExportDialog()
        if dialog.exec() != ExportDialog.DialogCode.Accepted:
            return
        export_format = dialog.export_format()
        extension = EXPORT_FORMAT_EXTENSIONS[export_format]
        path_str, _selected_filter = QFileDialog.getSaveFileName(
            None, "Export Manuscript", "", f"*{extension}"
        )
        if not path_str:
            return
        output_path = Path(path_str)
        if output_path.suffix.lower() != extension:
            output_path = output_path.with_suffix(extension)
        if output_path.exists():
            answer = QMessageBox.question(
                None,
                "Overwrite File",
                f"'{output_path.name}' already exists. Overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        def _on_error(message: str) -> None:
            QMessageBox.warning(None, "Export Failed", message)

        def _on_success(path: Path) -> None:
            QMessageBox.information(None, "Export Complete", f"Exported to {path}")

        result = self._export_service.export(
            manuscript_id,
            export_format,
            output_path,
            preset=dialog.preset(),
            on_success=_on_success,
            on_error=_on_error,
        )
        if result.warnings:
            logger.info("Compile warnings: %s", [warning.message for warning in result.warnings])

    def _resolve_current_manuscript_id(self) -> UUID | None:
        if self.hierarchy is None:
            return None
        if self.selected_node_id is not None:
            node = self.hierarchy.get_node(self.selected_node_id)
            if node is not None:
                return node.manuscript_id
        manuscripts = self.hierarchy.list_manuscripts()
        return manuscripts[0].id if manuscripts else None

    def _cmd_navigate_back(self) -> None:
        node_id = self.navigation.go_back()
        if node_id is not None:
            self.reveal_and_open(node_id, record_navigation=False)

    def _cmd_navigate_forward(self) -> None:
        node_id = self.navigation.go_forward()
        if node_id is not None:
            self.reveal_and_open(node_id, record_navigation=False)

    def _cmd_reveal_in_binder(self) -> None:
        if self.selected_node_id is not None and self._binder_panel is not None:
            try:
                self._binder_panel.reveal_node(self.selected_node_id)
            except RuntimeError:
                self._binder_panel = None

    def _cmd_toggle_split(self) -> None:
        if self._editor_panel is not None:
            self._editor_panel.toggle_split()
