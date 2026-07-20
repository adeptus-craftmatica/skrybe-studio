from __future__ import annotations

from pathlib import Path

import pytest

from skrybe_studio.app.bootstrap import Application
from skrybe_studio.plugins.notes.plugin import NotesPlugin
from skrybe_studio.ui.main_window import MainWindow


def test_main_window_launches_without_a_project(loaded_application: Application, qtbot) -> None:
    window = MainWindow(loaded_application)
    qtbot.addWidget(window)
    window.show()

    assert window.isVisible()
    assert window.windowTitle() == "Skrybe Studio"


def test_main_window_can_switch_to_notes_workspace(loaded_application: Application, qtbot) -> None:
    window = MainWindow(loaded_application)
    qtbot.addWidget(window)
    window.show()

    window._switch_workspace("notes")

    assert loaded_application.workspaces.active is not None
    assert loaded_application.workspaces.active.id == "notes"


def test_main_window_reflects_created_project_in_status_bar(
    loaded_application: Application, qtbot, project_root: Path
) -> None:
    window = MainWindow(loaded_application)
    qtbot.addWidget(window)
    window.show()

    loaded_application.create_project(project_root, "Smoke Test")
    window._on_project_opened()

    assert "Smoke Test" in window.statusBar().currentMessage()


def test_main_window_launches_even_if_a_plugin_fails_to_register(
    application: Application, monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    def _boom(self: NotesPlugin, context: object) -> None:
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(NotesPlugin, "register", _boom)
    application.load_plugins()

    window = MainWindow(application)
    qtbot.addWidget(window)
    window.show()

    assert window.isVisible()
    assert any(f.category == "register_error" for f in application.plugin_failures)
