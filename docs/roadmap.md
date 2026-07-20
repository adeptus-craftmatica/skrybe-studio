# Roadmap

Skrybe Studio is being built in broad phases. This iteration delivers **0.1 Platform** only -
everything after it is directional, not committed or scheduled.

## 0.1 Platform (this iteration)

- Core plugin architecture: manifest validation, discovery, dependency ordering, lifecycle,
  isolated failure handling.
- Shared entity/relationship system, event bus, command registry, service locator.
- `.skrybe` project format; project create/open/close/validate; recent projects.
- Custom plugin migration coordinator.
- Qt Widgets desktop shell: docking, workspaces, command palette, theme system.
- Background job abstraction; undo/redo abstraction; shared search abstraction.
- Two reference plugins: **Notes** and **Asset Library**.
- Standalone plugin host, automated tests, CI, developer documentation.

## 0.2 Writing

- Manuscript editor plugin: chapters/scenes as entities, rich(er) text or Markdown-based
  editing, a proper document storage strategy under `documents/`.
- Real-time word/character counts and writing session tracking.
- Undo/redo wired through the manuscript editor as the primary demonstration of
  `core/undo` at scale.

## 0.3 Planning

- Story bible / worldbuilding plugin: characters, locations, factions, lore entries as
  entities, linked via relationships.
- Timeline plugin: events as entities, ordered and linked to manuscript scenes and
  story-bible entities.
- Relationship graph visualization as a workspace panel, built purely on the existing
  `Relationship` contract - no new core concept required.
- Expanded shared search covering the new plugins' content.

## 0.4 Publishing

- Export plugin(s): EPUB/PDF/DOCX output from manuscript + metadata.
- Backup coordination using the `backups/` directory reserved in the project format.
- Archive compression for project export/sharing (explicitly deferred in 0.1).

## 0.5 Intelligence

- Optional, explicitly opt-in AI-assisted workflows (drafting assistance, consistency
  checking against the story bible, research summarization).
- Any AI integration will be a plugin consuming core services through the same contracts as
  every other plugin - no AI-specific hooks in `core/`.

## Ongoing, cross-cutting

- Full Alembic migration support if/when the custom coordinator's simplicity stops scaling.
- Secure credential storage (settings API is already designed to allow this without a
  breaking change).
- Packaging/distribution (installers, code signing) once the plugin surface stabilizes.
