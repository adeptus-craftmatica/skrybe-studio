"""A minimal shell that renders exactly one plugin's registered workspace panels.

By convention (documented in `docs/plugin-development.md`), a plugin's
primary workspace ID is the last dot-segment of its manifest ID (e.g.
`com.adeptus-craftmatica.skrybe.notes` -> workspace id `notes`), so the
host can locate it without any plugin-specific code.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QLabel, QMainWindow

from skrybe_studio.app.bootstrap import Application
from skrybe_studio.core.plugins.loader import LoadedPlugin
from skrybe_studio.ui.design_tokens import build_stylesheet

logger = logging.getLogger(__name__)

_AREA_MAP = {
    "left": Qt.DockWidgetArea.LeftDockWidgetArea,
    "right": Qt.DockWidgetArea.RightDockWidgetArea,
    "bottom": Qt.DockWidgetArea.BottomDockWidgetArea,
}


class PluginHostWindow(QMainWindow):
    def __init__(self, application: Application, target: LoadedPlugin) -> None:
        super().__init__()
        self._app = application
        self.setWindowTitle(f"Skrybe Studio Plugin Host — {target.manifest.name}")
        self.resize(1000, 700)
        self.setStyleSheet(build_stylesheet(application.theme.tokens))

        workspace_id = target.manifest.id.rsplit(".", 1)[-1]
        workspace = application.workspaces.get(workspace_id)
        if workspace is None:
            self.setCentralWidget(
                QLabel(
                    f"Plugin '{target.manifest.id}' registered no workspace named '{workspace_id}'."
                )
            )
            return

        for placement in workspace.panels:
            try:
                widget = application.panels.create(placement.panel_id)
            except KeyError:
                logger.warning("Unknown panel '%s'", placement.panel_id)
                continue
            dock = QDockWidget(application.panels.title_for(placement.panel_id))
            dock.setWidget(widget)
            area = _AREA_MAP.get(placement.area, Qt.DockWidgetArea.LeftDockWidgetArea)
            self.addDockWidget(area, dock)

        if workspace.central_panel_id is not None:
            try:
                self.setCentralWidget(application.panels.create(workspace.central_panel_id))
            except KeyError:
                logger.warning("Unknown central panel '%s'", workspace.central_panel_id)
