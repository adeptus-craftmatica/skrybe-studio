# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
will adopt [Semantic Versioning](https://semver.org/) once it reaches 1.0.

## [0.2.0] - Unreleased

### Added

- **Manuscript** plugin (`com.adeptus-craftmatica.skrybe.manuscript`): the first major
  creative-domain plugin.
  - Manuscript creation from local templates (Blank Novel, Three-Act Novel, Short Story,
    Nonfiction Book) and a binder-style hierarchy (manuscript/folder/part/chapter/scene/
    document) with type-validated parent-child rules and cycle prevention.
  - A tabbed, splittable document editor with focus mode, typewriter scrolling, find/replace,
    zoom, and debounced autosave with explicit flush points.
  - An inspector for metadata, status, label, tags, synopsis, compile-inclusion, and per-node
    word-count targets.
  - Writing goals: per-node targets and daily net-word-delta tracking.
  - Snapshots with diff-against-current and restore, taking an automatic safety snapshot first.
  - Local manuscript search contributing into shared cross-plugin search, plus back/forward
    navigation history scoped to document views.
  - A typed compile pipeline with plain-text, Markdown, HTML, and DOCX exporters and presets
    (Full Manuscript, Submission Draft, Plain Backup); exporting runs as a background job.
  - Optional cover-image integration with the Asset Library plugin, degrading gracefully when
    Asset Library is disabled or unavailable.
- `AssetLookup` protocol (`core/contracts/asset_lookup.py`): a minimal, domain-neutral core
  contract letting a plugin advertise a "resolve entity to display data" capability without any
  plugin importing another's implementation classes. The Asset Library plugin registers an
  adapter; Manuscript consumes it for cover images.
- Lightweight, dependency-free fuzzy matching (`core/commands/fuzzy.py`) for the command
  palette, replacing plain substring filtering.
- Tab-based workspace switching: each workspace is now a persistent tab whose panels are built
  once and cached (rebuilt only when the open project changes), replacing the dropdown that
  destroyed and rebuilt every panel - including scroll position, selection, and search text -
  on every switch. `find_enclosing_main_window()` (`core/workspaces/panels.py`) lets a plugin
  find the dock layout it belongs to for cross-cutting behavior like Manuscript's focus mode,
  scoped correctly to its own workspace tab rather than every workspace's docks at once.

## [0.1.0] - 2026-07-20

### Added

- Core platform: entity/relationship services, synchronous event bus, command registry,
  plugin manifest validation and loader (with dependency ordering, duplicate/circular
  detection, and isolated failure handling), `.skrybe` project lifecycle, a custom plugin
  migration coordinator, application/project/plugin-scoped settings, workspace and panel
  registries, a background job abstraction, an undo/redo abstraction, a shared search
  abstraction, and a design-token-driven theme system (light/dark/system).
- Qt Widgets desktop shell: main window with menus, toolbar, docking, workspace switching,
  a command palette, project creation/opening dialogs, a plugin manager dialog, and persisted
  window geometry.
- Notes reference plugin: create/rename/edit/delete/search notes with tags and live word
  count, backed by the shared entity system.
- Asset Library reference plugin: import images with background SHA-256 hashing and
  thumbnail generation, duplicate detection, tagging, and missing-file detection.
- A standalone plugin host (`skrybe-plugin-host`) for running a single plugin during
  development.
- GitHub Actions CI (Ubuntu/Windows/macOS), issue/PR templates, CODEOWNERS, and Dependabot
  configuration.
- Developer documentation: architecture, plugin development, project format, and roadmap.
