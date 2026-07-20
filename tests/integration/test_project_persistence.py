"""Verifies the golden path: create a project, write a note, close, reopen, and find it intact."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from skrybe_studio.app.bootstrap import Application
from skrybe_studio.app.paths import ApplicationPaths
from skrybe_studio.plugins.notes.plugin import NotesPlugin

NOTES_ID = "com.adeptus-craftmatica.skrybe.notes"


def _notes_plugin(application: Application) -> NotesPlugin:
    return cast(
        NotesPlugin,
        next(
            loaded.instance
            for loaded in application.loaded_plugins
            if loaded.manifest.id == NOTES_ID
        ),
    )


def test_note_persists_across_close_and_reopen(
    app_paths: ApplicationPaths, project_root: Path
) -> None:
    app = Application(paths=app_paths)
    app.load_plugins()
    project = app.create_project(project_root, "Persistence Test")
    saved_root = project.paths.root

    notes_plugin = _notes_plugin(app)
    assert notes_plugin.service is not None
    note = notes_plugin.service.create_note("Persisted Note", body="still here")

    app.close_project()
    app.shutdown()

    reopened_app = Application(paths=app_paths)
    reopened_app.load_plugins()
    reopened_app.open_project(saved_root)

    reopened_notes_plugin = _notes_plugin(reopened_app)
    assert reopened_notes_plugin.service is not None
    reloaded_note = reopened_notes_plugin.service.get_note(note.id)

    assert reloaded_note is not None
    assert reloaded_note.title == "Persisted Note"
    assert reloaded_note.body == "still here"

    reopened_app.close_project()
    reopened_app.shutdown()
