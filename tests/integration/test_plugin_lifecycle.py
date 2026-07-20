from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from skrybe_studio.app.bootstrap import Application
from skrybe_studio.plugins.notes.plugin import NotesPlugin

NOTES_ID = "com.adeptus-craftmatica.skrybe.notes"
ASSETS_ID = "com.adeptus-craftmatica.skrybe.assets"


def test_load_plugins_discovers_notes_and_assets(loaded_application: Application) -> None:
    ids = {loaded.manifest.id for loaded in loaded_application.loaded_plugins}

    assert ids == {NOTES_ID, ASSETS_ID}
    assert loaded_application.plugin_failures == []


def test_broken_plugin_register_does_not_prevent_other_plugins_loading(
    application: Application, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(self: NotesPlugin, context: object) -> None:
        raise RuntimeError("simulated register failure")

    monkeypatch.setattr(NotesPlugin, "register", _boom)

    application.load_plugins()

    loaded_ids = {loaded.manifest.id for loaded in application.loaded_plugins}
    assert NOTES_ID not in loaded_ids
    assert ASSETS_ID in loaded_ids
    assert any(f.category == "register_error" for f in application.plugin_failures)


def _notes_plugin(application: Application) -> NotesPlugin:
    return cast(
        NotesPlugin,
        next(
            loaded.instance
            for loaded in application.loaded_plugins
            if loaded.manifest.id == NOTES_ID
        ),
    )


def test_opening_a_project_activates_plugins(
    loaded_application: Application, project_root: Path
) -> None:
    notes_plugin = _notes_plugin(loaded_application)
    assert notes_plugin.service is None

    loaded_application.create_project(project_root, "Test Project")

    assert notes_plugin.service is not None


def test_closing_a_project_deactivates_plugins(
    loaded_application: Application, project_root: Path
) -> None:
    notes_plugin = _notes_plugin(loaded_application)
    loaded_application.create_project(project_root, "Test Project")

    loaded_application.close_project()

    assert notes_plugin.service is None


def test_shutdown_is_safe_without_an_open_project(loaded_application: Application) -> None:
    loaded_application.shutdown()
