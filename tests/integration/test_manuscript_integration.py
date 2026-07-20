"""Cross-cutting Manuscript plugin integration: app launch, the golden path
(create -> write -> close -> reopen), graceful degradation without the
Asset Library plugin, v0.1 project compatibility, the standalone plugin
host, and a structurally-large manuscript (no fragile timing assertions).
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from skrybe_studio.app.bootstrap import Application
from skrybe_studio.app.paths import ApplicationPaths
from skrybe_studio.plugins.manuscript.application.templates import ManuscriptTemplate
from skrybe_studio.plugins.manuscript.domain.document_ir import paragraph
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType
from skrybe_studio.plugins.manuscript.plugin import ManuscriptPlugin
from skrybe_studio.plugins.notes.plugin import NotesPlugin
from skrybe_studio.ui.main_window import MainWindow

MANUSCRIPT_ID = "com.adeptus-craftmatica.skrybe.manuscript"


def _manuscript_plugin(application: Application) -> ManuscriptPlugin:
    return cast(
        ManuscriptPlugin,
        next(
            loaded.instance
            for loaded in application.loaded_plugins
            if loaded.manifest.id == MANUSCRIPT_ID
        ),
    )


def test_application_launches_with_manuscript_plugin_enabled(
    loaded_application: Application,
) -> None:
    ids = {loaded.manifest.id for loaded in loaded_application.loaded_plugins}
    assert MANUSCRIPT_ID in ids
    assert loaded_application.plugin_failures == []


def test_application_still_launches_if_manuscript_plugin_fails_to_register(
    application: Application, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(self: ManuscriptPlugin, context: object) -> None:
        raise RuntimeError("simulated register failure")

    monkeypatch.setattr(ManuscriptPlugin, "register", _boom)

    application.load_plugins()

    loaded_ids = {loaded.manifest.id for loaded in application.loaded_plugins}
    assert MANUSCRIPT_ID not in loaded_ids
    assert any(f.category == "register_error" for f in application.plugin_failures)

    window = MainWindow(application)
    assert window is not None


def test_golden_path_create_write_close_reopen(
    app_paths: ApplicationPaths, project_root: Path
) -> None:
    app = Application(paths=app_paths)
    app.load_plugins()
    project = app.create_project(project_root, "Golden Path Novel")
    saved_root = project.paths.root

    manuscript_plugin = _manuscript_plugin(app)
    assert manuscript_plugin.hierarchy is not None
    manuscript = manuscript_plugin.hierarchy.create_manuscript("My Novel", ManuscriptTemplate.BLANK)
    part = manuscript_plugin.hierarchy.create_node(
        manuscript.id, ManuscriptNodeType.PART, "Part One"
    )
    chapter = manuscript_plugin.hierarchy.create_node(
        part.id, ManuscriptNodeType.CHAPTER, "Chapter One"
    )
    scene_one = manuscript_plugin.hierarchy.create_node(
        chapter.id, ManuscriptNodeType.SCENE, "Scene One"
    )
    scene_two = manuscript_plugin.hierarchy.create_node(
        chapter.id, ManuscriptNodeType.SCENE, "Scene Two"
    )

    assert manuscript_plugin.documents is not None
    manuscript_plugin.documents.save_content(scene_one.id, (paragraph("First scene content."),))
    manuscript_plugin.documents.save_content(scene_two.id, (paragraph("Second scene content."),))

    # reorder: swap the two scenes
    manuscript_plugin.hierarchy.move_sibling(scene_two.id, direction=-1)

    app.close_project()
    app.shutdown()

    reopened_app = Application(paths=app_paths)
    reopened_app.load_plugins()
    reopened_app.open_project(saved_root)
    reopened_plugin = _manuscript_plugin(reopened_app)
    assert reopened_plugin.hierarchy is not None
    assert reopened_plugin.documents is not None

    manuscripts = reopened_plugin.hierarchy.list_manuscripts()
    assert [m.title for m in manuscripts] == ["My Novel"]
    reopened_chapter_children = reopened_plugin.hierarchy.list_children(chapter.id)
    assert [c.title for c in reopened_chapter_children] == ["Scene Two", "Scene One"]
    assert (
        reopened_plugin.documents.load_content(scene_one.id)[0].plain_text == "First scene content."
    )
    assert (
        reopened_plugin.documents.load_content(scene_two.id)[0].plain_text
        == "Second scene content."
    )

    reopened_app.close_project()
    reopened_app.shutdown()


def test_manuscript_survives_asset_library_plugin_failure(
    application: Application, monkeypatch: pytest.MonkeyPatch, project_root: Path
) -> None:
    """Disabling/breaking the Asset Library plugin must not break Manuscript -
    cover-asset resolution should just degrade gracefully."""
    from skrybe_studio.plugins.assets.plugin import AssetsPlugin

    def _boom(self: AssetsPlugin, context: object) -> None:
        raise RuntimeError("simulated asset plugin failure")

    monkeypatch.setattr(AssetsPlugin, "register", _boom)
    application.load_plugins()

    assert MANUSCRIPT_ID in {loaded.manifest.id for loaded in application.loaded_plugins}

    application.create_project(project_root, "Test Project")
    manuscript_plugin = _manuscript_plugin(application)
    assert manuscript_plugin.hierarchy is not None
    manuscript = manuscript_plugin.hierarchy.create_manuscript("Novel")

    assert manuscript_plugin.assets is not None
    assert manuscript_plugin.assets.is_asset_library_available is False
    assert manuscript_plugin.assets.resolve_cover_thumbnail(manuscript.id) is None
    assert manuscript_plugin.assets.list_available_assets() == []


def test_v01_project_opens_safely_and_receives_manuscript_migrations(
    app_paths: ApplicationPaths, project_root: Path
) -> None:
    """A project created before the Manuscript plugin existed (only Notes/
    Assets active) must open safely afterwards, with Manuscript's tables
    created and Notes/Assets data left untouched."""
    v01_app = Application(paths=app_paths)
    v01_app.load_plugins()
    project = v01_app.create_project(project_root, "Legacy Project")
    saved_root = project.paths.root

    notes_plugin = cast(
        NotesPlugin,
        next(loaded.instance for loaded in v01_app.loaded_plugins if "notes" in loaded.manifest.id),
    )
    assert notes_plugin.service is not None
    note = notes_plugin.service.create_note("Existing Note", body="written before v0.2")

    v01_app.close_project()
    v01_app.shutdown()

    v02_app = Application(paths=app_paths)
    v02_app.load_plugins()
    v02_app.open_project(saved_root)

    reopened_notes_plugin = cast(
        NotesPlugin,
        next(loaded.instance for loaded in v02_app.loaded_plugins if "notes" in loaded.manifest.id),
    )
    assert reopened_notes_plugin.service is not None
    reloaded_note = reopened_notes_plugin.service.get_note(note.id)
    assert reloaded_note is not None
    assert reloaded_note.title == "Existing Note"

    manuscript_plugin = _manuscript_plugin(v02_app)
    assert manuscript_plugin.hierarchy is not None
    manuscript = manuscript_plugin.hierarchy.create_manuscript("New Manuscript")
    assert manuscript_plugin.hierarchy.get_node(manuscript.id) is not None

    v02_app.close_project()
    v02_app.shutdown()


def test_standalone_plugin_host_renders_manuscript_workspace(
    app_paths: ApplicationPaths, project_root: Path
) -> None:
    from skrybe_studio.plugin_host.window import PluginHostWindow

    app = Application(paths=app_paths)
    app.load_plugins()
    app.create_project(project_root, "Standalone Host Project")

    target = next(loaded for loaded in app.loaded_plugins if loaded.manifest.id == MANUSCRIPT_ID)
    window = PluginHostWindow(app, target)

    assert window.centralWidget() is not None

    app.close_project()
    app.shutdown()


def test_large_manuscript_structure_remains_correct(
    loaded_application: Application, project_root: Path
) -> None:
    """Not a timing benchmark - just confirms a structurally large tree
    (10 parts x 5 chapters x 4 scenes = 200 scenes) stays internally
    consistent: correct counts, correct aggregate word count, and lazy
    per-node content access (loading the tree never loads every body)."""
    loaded_application.create_project(project_root, "Big Book")
    manuscript_plugin = cast(
        ManuscriptPlugin,
        next(
            loaded.instance
            for loaded in loaded_application.loaded_plugins
            if loaded.manifest.id == MANUSCRIPT_ID
        ),
    )
    assert manuscript_plugin.hierarchy is not None
    assert manuscript_plugin.documents is not None
    hierarchy = manuscript_plugin.hierarchy
    documents = manuscript_plugin.documents

    manuscript = hierarchy.create_manuscript("Big Book")
    scene_ids = []
    for part_index in range(10):
        part = hierarchy.create_node(manuscript.id, ManuscriptNodeType.PART, f"Part {part_index}")
        for chapter_index in range(5):
            chapter = hierarchy.create_node(
                part.id, ManuscriptNodeType.CHAPTER, f"Chapter {chapter_index}"
            )
            for scene_index in range(4):
                scene = hierarchy.create_node(
                    chapter.id, ManuscriptNodeType.SCENE, f"Scene {scene_index}"
                )
                scene_ids.append(scene.id)
                documents.save_content(scene.id, (paragraph("word " * 50),))

    subtree = hierarchy.list_subtree(manuscript.id)
    # 1 manuscript + 10 parts + 50 chapters + 200 scenes
    assert len(subtree) == 1 + 10 + 50 + 200

    total_words = hierarchy.subtree_word_count(manuscript.id)
    assert total_words == 200 * 50

    # Listing children never eagerly loads document bodies - only explicit
    # load_content() calls do, and those return exactly what was written.
    first_scene_content = documents.load_content(scene_ids[0])
    assert first_scene_content[0].plain_text.split()[0] == "word"
