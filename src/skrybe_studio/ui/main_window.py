"""The main application window: menus, toolbar, docking, workspaces, and dialogs.

This module only orchestrates generic core concepts (workspaces, panels,
commands, projects, plugins, theme) - it never imports a plugin's
concrete panel or command classes directly.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QActionGroup, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDockWidget,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from skrybe_studio.app.bootstrap import Application
from skrybe_studio.core.errors import set_error_presenter
from skrybe_studio.core.projects.errors import ProjectError
from skrybe_studio.core.themes.manager import ThemeMode
from skrybe_studio.core.themes.tokens import DesignTokens
from skrybe_studio.ui.design_tokens import build_stylesheet
from skrybe_studio.ui.dialogs.command_palette import CommandPalette
from skrybe_studio.ui.dialogs.create_project_dialog import CreateProjectDialog
from skrybe_studio.ui.dialogs.error_dialog import ErrorDialog
from skrybe_studio.ui.dialogs.open_project_dialog import OpenProjectDialog
from skrybe_studio.ui.dialogs.plugin_manager_dialog import PluginManagerDialog

logger = logging.getLogger(__name__)

_DEFAULT_WORKSPACE_ID = "default"

_AREA_MAP = {
    "left": Qt.DockWidgetArea.LeftDockWidgetArea,
    "right": Qt.DockWidgetArea.RightDockWidgetArea,
    "bottom": Qt.DockWidgetArea.BottomDockWidgetArea,
}


class MainWindow(QMainWindow):
    def __init__(self, application: Application) -> None:
        super().__init__()
        self._app = application
        self._dock_widgets: list[QDockWidget] = []

        self.setWindowTitle("Skrybe Studio")
        self.resize(1280, 820)

        self._build_menus()
        self._build_toolbar()
        self._build_central_area()
        self.setStatusBar(QStatusBar())

        self._app.theme.theme_changed.connect(self._apply_theme)
        self._apply_theme(self._app.theme.tokens)

        set_error_presenter(self._present_error)

        self._restore_window_state()
        self._refresh_workspace_menu()
        active = self._app.workspaces.active
        self._switch_workspace(active.id if active else _DEFAULT_WORKSPACE_ID)
        self._update_status_bar()

    # --- menu / toolbar construction ---------------------------------------

    def _build_menus(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        new_action = file_menu.addAction("&New Project…")
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._on_new_project)

        open_action = file_menu.addAction("&Open Project…")
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._on_open_project)

        self._recent_menu = file_menu.addMenu("Open &Recent")
        self._refresh_recent_menu()

        file_menu.addSeparator()
        close_action = file_menu.addAction("&Close Project")
        close_action.triggered.connect(self._on_close_project)

        file_menu.addSeparator()
        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)

        view_menu = menu_bar.addMenu("&View")
        theme_menu = view_menu.addMenu("Theme")
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        for mode in ThemeMode:
            action = theme_menu.addAction(mode.value.title())
            action.setCheckable(True)
            action.setChecked(self._app.theme.mode == mode)
            action.triggered.connect(lambda _checked, m=mode: self._app.theme.set_mode(m))
            theme_group.addAction(action)

        view_menu.addSeparator()
        palette_action = view_menu.addAction("Command &Palette…")
        palette_action.setShortcut(QKeySequence("Ctrl+K"))
        palette_action.triggered.connect(self._on_command_palette)

        self._workspace_menu = menu_bar.addMenu("&Workspace")

        plugins_menu = menu_bar.addMenu("&Plugins")
        manage_action = plugins_menu.addAction("&Manage Plugins…")
        manage_action.triggered.connect(self._on_manage_plugins)

        help_menu = menu_bar.addMenu("&Help")
        about_action = help_menu.addAction("&About Skrybe Studio")
        about_action.triggered.connect(self._on_about)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction("New Project", self._on_new_project)
        toolbar.addAction("Open Project", self._on_open_project)
        toolbar.addSeparator()
        toolbar.addAction("Command Palette", self._on_command_palette)
        toolbar.addSeparator()

        self._workspace_combo = QComboBox()
        # AdjustToContents (rather than the default AdjustToContentsOnFirstShow)
        # keeps the box sized to whatever the longest current item needs,
        # even if workspaces are added/renamed after the first show. The
        # minimum width is a floor so it never looks cramped with only the
        # default single short-named workspace registered.
        self._workspace_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._workspace_combo.setMinimumWidth(140)
        self._workspace_combo.currentIndexChanged.connect(self._on_workspace_combo_changed)
        toolbar.addWidget(self._workspace_combo)

    def _build_central_area(self) -> None:
        self._central_stack = QStackedWidget()
        self._welcome_widget = self._build_welcome_widget()
        self._central_stack.addWidget(self._welcome_widget)
        self.setCentralWidget(self._central_stack)

    def _build_welcome_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Skrybe Studio")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Create or open a project to begin.")
        subtitle.setObjectName("muted")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        return widget

    # --- theme ---------------------------------------------------------------

    def _apply_theme(self, tokens: DesignTokens) -> None:
        self.setStyleSheet(build_stylesheet(tokens))

    # --- workspace switching ---------------------------------------------------

    def _refresh_workspace_menu(self) -> None:
        self._workspace_menu.clear()
        self._workspace_combo.blockSignals(True)
        self._workspace_combo.clear()
        group = QActionGroup(self)
        group.setExclusive(True)
        for workspace in self._app.workspaces.all():
            action = self._workspace_menu.addAction(workspace.title)
            action.setCheckable(True)
            action.triggered.connect(lambda _checked, wid=workspace.id: self._switch_workspace(wid))
            group.addAction(action)
            self._workspace_combo.addItem(workspace.title, workspace.id)
        self._workspace_combo.blockSignals(False)

    def _on_workspace_combo_changed(self, index: int) -> None:
        workspace_id = self._workspace_combo.itemData(index)
        if workspace_id:
            self._switch_workspace(workspace_id)

    def _switch_workspace(self, workspace_id: str) -> None:
        workspace = self._app.workspaces.get(workspace_id)
        if workspace is None:
            return
        self._app.workspaces.set_active(workspace_id)
        self._teardown_dock_widgets()

        for placement in workspace.panels:
            try:
                widget = self._app.panels.create(placement.panel_id)
            except KeyError:
                logger.warning(
                    "Workspace '%s' references unknown panel '%s'", workspace_id, placement.panel_id
                )
                continue
            dock = QDockWidget(self._app.panels.title_for(placement.panel_id))
            dock.setObjectName(f"dock.{placement.panel_id}")
            dock.setWidget(widget)
            area = _AREA_MAP.get(placement.area, Qt.DockWidgetArea.LeftDockWidgetArea)
            self.addDockWidget(area, dock)
            self._dock_widgets.append(dock)

        if workspace.central_panel_id is not None:
            try:
                central_widget = self._app.panels.create(workspace.central_panel_id)
                self._central_stack.addWidget(central_widget)
                self._central_stack.setCurrentWidget(central_widget)
            except KeyError:
                self._central_stack.setCurrentWidget(self._welcome_widget)
        else:
            self._central_stack.setCurrentWidget(self._welcome_widget)

        index = self._workspace_combo.findData(workspace_id)
        if index >= 0:
            # Block signals: setCurrentIndex would otherwise fire
            # currentIndexChanged -> _on_workspace_combo_changed -> a second,
            # redundant call back into this same method, double-building
            # every panel in the workspace.
            self._workspace_combo.blockSignals(True)
            self._workspace_combo.setCurrentIndex(index)
            self._workspace_combo.blockSignals(False)
        self._app.settings.set_app("last_workspace", workspace_id)

    def _teardown_dock_widgets(self) -> None:
        for dock in self._dock_widgets:
            self.removeDockWidget(dock)
            dock.deleteLater()
        self._dock_widgets.clear()

    # --- project actions ---------------------------------------------------

    def _on_new_project(self) -> None:
        dialog = CreateProjectDialog(Path.home(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name = dialog.project_name()
        if not name:
            QMessageBox.warning(self, "Create Project", "Please enter a project name.")
            return
        try:
            self._app.create_project(dialog.project_root(), name)
        except ProjectError as exc:
            QMessageBox.critical(self, "Create Project", str(exc))
            return
        self._on_project_opened()

    def _on_open_project(self) -> None:
        dialog = OpenProjectDialog(self._app.projects.recent_projects.all(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        path = dialog.selected_path()
        if path is None:
            return
        self._open_path(path)

    def _open_path(self, path: Path) -> None:
        try:
            self._app.open_project(path)
        except ProjectError as exc:
            QMessageBox.critical(self, "Open Project", str(exc))
            return
        self._on_project_opened()

    def _on_project_opened(self) -> None:
        self._refresh_recent_menu()
        active = self._app.workspaces.active
        self._switch_workspace(active.id if active else _DEFAULT_WORKSPACE_ID)
        self._update_status_bar()

    def _on_close_project(self) -> None:
        self._app.close_project()
        self._update_status_bar()
        self._switch_workspace(_DEFAULT_WORKSPACE_ID)

    def _refresh_recent_menu(self) -> None:
        self._recent_menu.clear()
        for entry in self._app.projects.recent_projects.all():
            path = entry.get("path")
            if not path:
                continue
            action = self._recent_menu.addAction(f"{entry.get('name', '?')}  —  {path}")
            action.triggered.connect(lambda _checked, p=path: self._open_path(Path(p)))

    # --- plugins / palette / about -----------------------------------------

    def _on_manage_plugins(self) -> None:
        dialog = PluginManagerDialog(self._app.loaded_plugins, self._app.plugin_failures, self)
        dialog.exec()

    def _on_command_palette(self) -> None:
        dialog = CommandPalette(self._app.commands, self)
        dialog.exec()

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About Skrybe Studio",
            "Skrybe Studio 0.1.0\n"
            "A desktop-first creative operating system for writers.\n\n"
            "https://github.com/adeptus-craftmatica/skrybe-studio",
        )

    def _update_status_bar(self) -> None:
        status = self.statusBar()
        project = self._app.projects.current
        project_text = (
            f"Project: {project.metadata.name}" if project is not None else "No project open"
        )
        status.showMessage(f"{project_text}   |   Plugins: {len(self._app.loaded_plugins)}")

    # --- errors ----------------------------------------------------------------

    def _present_error(self, summary: str, technical_detail: str) -> None:
        ErrorDialog(summary, technical_detail, self).exec()

    # --- window geometry persistence -------------------------------------------

    def _restore_window_state(self) -> None:
        geometry_b64 = self._app.settings.get_app("window.geometry")
        state_b64 = self._app.settings.get_app("window.state")
        if geometry_b64:
            self.restoreGeometry(QByteArray(base64.b64decode(geometry_b64)))
        if state_b64:
            self.restoreState(QByteArray(base64.b64decode(state_b64)))

    def closeEvent(self, event: QCloseEvent) -> None:
        self._app.settings.set_app(
            "window.geometry", base64.b64encode(self.saveGeometry().data()).decode("ascii")
        )
        self._app.settings.set_app(
            "window.state", base64.b64encode(self.saveState().data()).decode("ascii")
        )
        self._app.shutdown()
        super().closeEvent(event)
