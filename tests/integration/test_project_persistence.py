"""Verifies the golden path: create a project, write a note, close, reopen, and find it intact."""

from __future__ import annotations

import shutil
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


def test_quitting_with_a_project_open_reopens_it_on_next_launch(
    app_paths: ApplicationPaths, project_root: Path
) -> None:
    app = Application(paths=app_paths)
    app.load_plugins()
    project = app.create_project(project_root, "Reopen Test")
    saved_root = project.paths.root

    # shutdown() closes the project as part of normal teardown, but not via
    # an explicit "Close Project" - it must still be remembered as "was open
    # when the app last quit."
    app.shutdown()

    relaunched_app = Application(paths=app_paths)
    relaunched_app.load_plugins()
    reopened = relaunched_app.reopen_last_project()

    assert reopened is not None
    assert reopened.paths.root == saved_root
    assert relaunched_app.projects.current is not None

    relaunched_app.close_project()
    relaunched_app.shutdown()


def test_explicitly_closing_a_project_means_next_launch_does_not_reopen_it(
    app_paths: ApplicationPaths, project_root: Path
) -> None:
    app = Application(paths=app_paths)
    app.load_plugins()
    app.create_project(project_root, "Forget Test")

    app.close_project(forget=True)
    app.shutdown()

    relaunched_app = Application(paths=app_paths)
    relaunched_app.load_plugins()

    assert relaunched_app.reopen_last_project() is None
    assert relaunched_app.projects.current is None

    relaunched_app.shutdown()


def test_reopen_last_project_gracefully_handles_a_deleted_project(
    app_paths: ApplicationPaths, project_root: Path
) -> None:
    app = Application(paths=app_paths)
    app.load_plugins()
    project = app.create_project(project_root, "Deleted Test")
    saved_root = project.paths.root
    app.shutdown()
    shutil.rmtree(saved_root)

    relaunched_app = Application(paths=app_paths)
    relaunched_app.load_plugins()

    assert relaunched_app.reopen_last_project() is None
    assert relaunched_app.settings.get_app("last_open_project_path") is None

    relaunched_app.shutdown()
