# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
will adopt [Semantic Versioning](https://semver.org/) once it reaches 1.0.

## [0.1.0] - Unreleased

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
