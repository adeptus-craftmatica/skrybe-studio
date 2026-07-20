from __future__ import annotations

import pytest

from skrybe_studio.core.workspaces.models import PanelPlacement, Workspace
from skrybe_studio.core.workspaces.panels import (
    DuplicatePanelError,
    PanelRegistry,
    find_enclosing_main_window,
)
from skrybe_studio.core.workspaces.registry import DuplicateWorkspaceError, WorkspaceRegistry


def test_first_registered_workspace_becomes_active() -> None:
    registry = WorkspaceRegistry()
    registry.register(Workspace(id="default", title="Default"))

    active = registry.active
    assert active is not None
    assert active.id == "default"


def test_set_active_switches_workspace() -> None:
    registry = WorkspaceRegistry()
    registry.register(Workspace(id="default", title="Default"))
    registry.register(Workspace(id="notes", title="Notes"))

    registry.set_active("notes")

    active = registry.active
    assert active is not None
    assert active.id == "notes"


def test_duplicate_workspace_id_raises() -> None:
    registry = WorkspaceRegistry()
    registry.register(Workspace(id="default", title="Default"))

    with pytest.raises(DuplicateWorkspaceError):
        registry.register(Workspace(id="default", title="Default Again"))


def test_set_active_unknown_workspace_raises() -> None:
    registry = WorkspaceRegistry()
    with pytest.raises(KeyError):
        registry.set_active("does-not-exist")


def test_workspace_panels_reference_ids_not_classes() -> None:
    workspace = Workspace(
        id="notes",
        title="Notes",
        central_panel_id="notes.editor",
        panels=(PanelPlacement(panel_id="notes.browser", area="left"),),
    )
    assert workspace.panels[0].panel_id == "notes.browser"
    assert workspace.central_panel_id == "notes.editor"


def test_panel_registry_creates_widget_via_factory(qapp) -> None:
    from PySide6.QtWidgets import QLabel

    registry = PanelRegistry()
    registry.register("demo.panel", "Demo", lambda: QLabel("hello"))

    widget = registry.create("demo.panel")

    assert isinstance(widget, QLabel)
    assert registry.title_for("demo.panel") == "Demo"


def test_panel_registry_duplicate_id_raises(qapp) -> None:
    from PySide6.QtWidgets import QLabel

    registry = PanelRegistry()
    registry.register("demo.panel", "Demo", lambda: QLabel("hello"))

    with pytest.raises(DuplicatePanelError):
        registry.register("demo.panel", "Demo Again", lambda: QLabel("hi"))


def test_panel_registry_unknown_panel_raises(qapp) -> None:
    registry = PanelRegistry()
    with pytest.raises(KeyError):
        registry.create("does-not-exist")


def test_find_enclosing_main_window_returns_none_without_an_ancestor(qapp) -> None:
    from PySide6.QtWidgets import QWidget

    widget = QWidget()
    assert find_enclosing_main_window(widget) is None


def test_find_enclosing_main_window_finds_a_direct_ancestor(qapp) -> None:
    from PySide6.QtWidgets import QLabel, QMainWindow

    main_window = QMainWindow()
    label = QLabel()
    main_window.setCentralWidget(label)

    assert find_enclosing_main_window(label) is main_window


def test_find_enclosing_main_window_finds_the_nearest_not_the_outermost(qapp) -> None:
    """A panel nested inside a per-workspace QMainWindow (itself embedded in the
    app's real top-level QMainWindow) must resolve to its own workspace's
    window, not the app's - otherwise dock-scoped behavior like focus mode
    would reach across every workspace instead of just its own.
    """
    from PySide6.QtWidgets import QLabel, QMainWindow

    outer = QMainWindow()
    inner = QMainWindow()
    label = QLabel()
    inner.setCentralWidget(label)
    outer.setCentralWidget(inner)

    assert find_enclosing_main_window(label) is inner
