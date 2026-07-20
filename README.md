# Skrybe Studio

**Skrybe Studio** is a desktop-first creative operating system for writers — not just another
text editor. It is being built as a modular platform for manuscript writing, story planning,
worldbuilding, research, asset management, timelines, relationship graphs, publishing, and
optional AI-assisted workflows.

> **Status: early architecture prototype (v0.1.0).**
> This iteration proves out the core/plugin architecture with a working desktop shell,
> project format, and two reference plugins (Notes, Asset Library). Manuscript editing,
> story bible, timelines, and other major creative features are **not yet implemented**.

Repository owner: **[adeptus-craftmatica](https://github.com/adeptus-craftmatica)**
Repository: <https://github.com/adeptus-craftmatica/skrybe-studio>

## Screenshots

_Placeholder — screenshots will be added once the UI stabilizes further._

## Product vision

Skrybe Studio is designed around a small, stable core and independently developed plugins:

1. **Everything is an entity.** Every object a plugin creates — a note, an asset, and later a
   character, scene, or timeline event — is a globally addressable `Entity`.
2. **Everything can link to other entities.** Cross-cutting `Relationship`s connect entities
   regardless of which plugin owns them.
3. **Major capabilities are plugins.** Manuscript writing, story planning, worldbuilding,
   research, timelines, relationship graphs, and publishing will all ship as plugins.
4. **Different screens are views over shared project data.** Workspaces arrange panels and
   commands; they don't own data.
5. **The core has no feature-specific knowledge.** It never imports or understands what a
   manuscript, timeline, or story bible is — see [`docs/architecture.md`](docs/architecture.md).

## Core principles

- A small core provides shared services: entities, relationships, events, commands, projects,
  workspaces, settings, storage, jobs, undo, search, and themes.
- Plugins own their domain logic, UI, persistence, and tests, and communicate only through
  entity IDs, events, service interfaces, capability registration, and commands — never by
  importing one another's implementation classes.
- A broken optional plugin must never prevent the application from starting.

## Implemented features (v0.1.0)

- Plugin system: manifest validation, discovery, dependency ordering, duplicate/circular
  detection, isolated failure handling, and a standalone plugin host.
- Shared entity and relationship services backed by SQLite (SQLAlchemy 2.x), with soft deletion.
- Synchronous, typed, error-isolated event bus and a command registry.
- `.skrybe` project format: create / open / close / validate, recent-projects tracking.
- A small, testable plugin migration coordinator (full Alembic integration deferred).
- Workspace and panel registries; a Qt Widgets main window shell with docking, a command
  palette, project dialogs, a plugin manager dialog, and light/dark/system theming driven by
  centralized design tokens.
- Background job abstraction (Qt thread pool) with cooperative cancellation.
- An undo/redo abstraction (Qt's `QUndoStack` behind a Qt-free domain contract).
- **Notes** reference plugin: create/rename/edit/delete notes, tags, word count, search
  contribution, entity registration (`notes.note`), standalone execution.
- **Asset Library** reference plugin: import images with thumbnails, SHA-256 duplicate
  detection, metadata, missing-file detection, entity registration (`assets.asset`), standalone
  execution.

## Planned plugins

Manuscript editor, story bible / worldbuilding, timelines, relationship graphs, research,
publishing/export, and optional AI-assisted workflows. See [`docs/roadmap.md`](docs/roadmap.md).

## Setup

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Running

```bash
uv run skrybe-studio
# or
uv run python -m skrybe_studio
```

Run a single plugin standalone (for plugin development):

```bash
uv run skrybe-plugin-host --plugin notes
```

## Testing

```bash
uv run pytest
```

## Linting and type checking

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
```

## Releasing

Maintainers cut a release with:

```bash
uv run python release.py
```

This builds a PyInstaller bundle for the current platform, packages it (`.dmg` on macOS, `.zip`
on Windows, `.tar.gz` on Linux), bumps the version in `pyproject.toml`, `src/skrybe_studio/
__init__.py`, and `SkrybeStudio.spec`, commits, tags `vX.Y.Z`, and pushes. Pushing the tag
triggers [`.github/workflows/release.yml`](.github/workflows/release.yml), which builds all
three platforms on their native GitHub-hosted runners and attaches the artifacts to a GitHub
Release. Builds are currently unsigned - macOS will show a Gatekeeper warning and Windows a
SmartScreen warning until code signing is added.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full core/plugin architecture,
[`docs/plugin-development.md`](docs/plugin-development.md) for building a plugin,
[`docs/project-format.md`](docs/project-format.md) for the `.skrybe` project layout, and
[`docs/roadmap.md`](docs/roadmap.md) for where this is headed.

## Contribution guidance

This is currently a private, early-stage project. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for
expectations around code style, testing, and the plugin architecture rules. All changes should
preserve the separation between core and plugins — see the architecture doc before adding
anything to `core/`.

## License

All rights reserved by `adeptus-craftmatica`. See [`LICENSE`](LICENSE). No open-source license
has been chosen; this may become a commercial product.

## Ownership

Maintained by **[adeptus-craftmatica](https://github.com/adeptus-craftmatica)**.
