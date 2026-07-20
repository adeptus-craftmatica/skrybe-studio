"""The central Writing Workspace panel: tabbed documents, one optional split, focus mode.

Focus mode and the split view are pure presentation state over the
existing dock widgets and tab widgets - there is no separate
persistence path or editor implementation for them. Focus mode hides
dock widgets by walking the top-level window's own child widgets
(`self.window().findChildren(QDockWidget)`), a stock Qt mechanism that
requires no import of - or hook into - the main window class itself, so
it works identically inside the full application shell and the
standalone plugin host.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QSplitter, QTabWidget, QVBoxLayout, QWidget

from skrybe_studio.core.contracts.event import Event
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.manuscript.application.events import NodeSelectionChanged
from skrybe_studio.plugins.manuscript.ui.editor.document_editor import DocumentEditor

if TYPE_CHECKING:
    from skrybe_studio.plugins.manuscript.plugin import ManuscriptPlugin

logger = logging.getLogger(__name__)


class EditorPanel(QWidget):
    def __init__(self, plugin: ManuscriptPlugin, events: EventBus) -> None:
        super().__init__()
        self._plugin = plugin
        self._events = events
        self._focus_mode_active = False
        self._hidden_docks: list[QDockWidget] = []

        self._primary_tabs = self._build_tab_widget()
        self._secondary_tabs: QTabWidget | None = None
        self._active_tabs = self._primary_tabs

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._primary_tabs)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._splitter)

        events.subscribe(NodeSelectionChanged, self._on_node_selected)
        plugin.set_editor_panel(self)
        self._restore_open_tabs()

    def _build_tab_widget(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.setTabsClosable(True)
        tabs.setMovable(True)
        tabs.tabCloseRequested.connect(lambda index, t=tabs: self._close_tab(t, index))
        tabs.currentChanged.connect(lambda _index, t=tabs: self._on_current_tab_changed(t))
        return tabs

    # --- opening documents -----------------------------------------------------

    def _on_node_selected(self, event: Event) -> None:
        if not isinstance(event, NodeSelectionChanged) or event.node_id is None:
            return
        if self._plugin.hierarchy is None:
            return
        node = self._plugin.hierarchy.get_node(event.node_id)
        if node is not None and node.is_text_bearing:
            self.open_document(event.node_id)

    def open_document(self, node_id: UUID, *, in_secondary: bool = False) -> None:
        """Opening can also happen indirectly, via `NodeSelectionChanged` triggering
        `_on_node_selected` above (e.g. when the binder reveals a node) - so
        navigation-history suppression lives on the plugin
        (`suppress_navigation_recording`), not as a parameter here, since both
        paths must respect it uniformly."""
        tabs = (
            self._secondary_tabs
            if in_secondary and self._secondary_tabs is not None
            else self._primary_tabs
        )
        for index in range(tabs.count()):
            widget = tabs.widget(index)
            if isinstance(widget, DocumentEditor) and widget.node_id == node_id:
                tabs.setCurrentIndex(index)
                self._active_tabs = tabs
                self._record_navigation(node_id)
                return

        editor = DocumentEditor(self._plugin, node_id)
        editor.set_typewriter_enabled(self._plugin.get_typewriter_enabled())
        node = self._plugin.hierarchy.get_node(node_id) if self._plugin.hierarchy else None
        index = tabs.addTab(editor, node.title if node is not None else "Untitled")
        editor.titleChanged.connect(
            lambda title, e=editor, t=tabs: self._update_tab_title(t, e, title)
        )
        tabs.setCurrentIndex(index)
        self._active_tabs = tabs
        self._record_navigation(node_id)
        self._persist_open_tabs()

    def show_find_bar(self) -> None:
        widget = self._active_tabs.currentWidget()
        if isinstance(widget, DocumentEditor):
            widget.show_find_bar()

    def _update_tab_title(self, tabs: QTabWidget, editor: DocumentEditor, title: str) -> None:
        index = tabs.indexOf(editor)
        if index >= 0:
            tabs.setTabText(index, title)

    def _record_navigation(self, node_id: UUID) -> None:
        if not self._plugin.suppress_navigation_recording:
            self._plugin.navigation.visit(node_id)
        self._plugin.set_selected_node(node_id)

    def _on_current_tab_changed(self, tabs: QTabWidget) -> None:
        self._active_tabs = tabs
        widget = tabs.currentWidget()
        if isinstance(widget, DocumentEditor):
            self._record_navigation(widget.node_id)

    def _close_tab(self, tabs: QTabWidget, index: int) -> None:
        widget = tabs.widget(index)
        if isinstance(widget, DocumentEditor):
            widget.flush()
        tabs.removeTab(index)
        if widget is not None:
            widget.deleteLater()
        self._persist_open_tabs()

    def current_node_id(self) -> UUID | None:
        widget = self._active_tabs.currentWidget()
        return widget.node_id if isinstance(widget, DocumentEditor) else None

    # --- lifecycle: never lose unsaved content --------------------------------------

    def flush_all(self) -> None:
        for tabs in self._all_tab_widgets():
            for index in range(tabs.count()):
                widget = tabs.widget(index)
                if isinstance(widget, DocumentEditor):
                    widget.flush()

    def _all_tab_widgets(self) -> list[QTabWidget]:
        widgets = [self._primary_tabs]
        if self._secondary_tabs is not None:
            widgets.append(self._secondary_tabs)
        return widgets

    # --- split view --------------------------------------------------------------------

    def toggle_split(self) -> None:
        if self._secondary_tabs is None:
            self._secondary_tabs = self._build_tab_widget()
            self._splitter.addWidget(self._secondary_tabs)
        else:
            for index in reversed(range(self._secondary_tabs.count())):
                self._close_tab(self._secondary_tabs, index)
            self._secondary_tabs.deleteLater()
            self._secondary_tabs = None
            self._active_tabs = self._primary_tabs

    # --- focus mode --------------------------------------------------------------------

    def toggle_focus_mode(self) -> None:
        top_level = self.window()
        dock_widgets = top_level.findChildren(QDockWidget)
        if not self._focus_mode_active:
            self._hidden_docks = [dock for dock in dock_widgets if dock.isVisible()]
            for dock in self._hidden_docks:
                dock.setVisible(False)
            self._focus_mode_active = True
        else:
            for dock in self._hidden_docks:
                try:
                    dock.setVisible(True)
                except RuntimeError:
                    logger.debug("A dock widget was deleted while focus mode was active")
            self._hidden_docks = []
            self._focus_mode_active = False

    @property
    def is_focus_mode_active(self) -> bool:
        return self._focus_mode_active

    # --- typewriter scrolling ----------------------------------------------------------

    def set_typewriter_enabled(self, enabled: bool) -> None:
        for tabs in self._all_tab_widgets():
            for index in range(tabs.count()):
                widget = tabs.widget(index)
                if isinstance(widget, DocumentEditor):
                    widget.set_typewriter_enabled(enabled)

    # --- persisted open tabs -----------------------------------------------------------

    def _persist_open_tabs(self) -> None:
        ids: list[str] = []
        for tabs in self._all_tab_widgets():
            for index in range(tabs.count()):
                widget = tabs.widget(index)
                if isinstance(widget, DocumentEditor):
                    ids.append(str(widget.node_id))
        self._plugin.set_open_tab_ids(ids)

    def _restore_open_tabs(self) -> None:
        if self._plugin.hierarchy is None:
            return
        for raw_id in self._plugin.get_open_tab_ids():
            try:
                node_id = UUID(raw_id)
            except ValueError:
                continue
            if self._plugin.hierarchy.get_node(node_id) is not None:
                self.open_document(node_id)
