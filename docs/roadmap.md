# Roadmap

Skrybe Studio is being built in broad phases. **0.1 Platform** and **0.2 Writing** are
delivered; everything after them is directional, not committed or scheduled.

## 0.1 Platform (delivered)

- Core plugin architecture: manifest validation, discovery, dependency ordering, lifecycle,
  isolated failure handling.
- Shared entity/relationship system, event bus, command registry, service locator.
- `.skrybe` project format; project create/open/close/validate; recent projects.
- Custom plugin migration coordinator.
- Qt Widgets desktop shell: docking, workspaces, command palette, theme system.
- Background job abstraction; undo/redo abstraction; shared search abstraction.
- Two reference plugins: **Notes** and **Asset Library**.
- Standalone plugin host, automated tests, CI, developer documentation.

## 0.2 Writing (delivered)

- **Manuscript** plugin: manuscript/folder/part/chapter/scene/document entities in a validated,
  cyclic-safe binder hierarchy, created from local templates. Document content is stored in the
  plugin's own `project.db` tables (`manuscript_document_content`), not as files under
  `documents/` - a proper document storage strategy turned out to mean "in the database," not a
  new on-disk format.
- A tabbed/split document editor with focus mode, typewriter scrolling, and real-time word
  counts; debounced autosave with explicit flush points rather than a separate writing-session
  tracker.
- Snapshots, writing goals (per-node targets + daily net-word-delta), local + shared search,
  and navigation history.
- Plain-text/Markdown/HTML/DOCX export with presets - originally scoped for **0.4 Publishing**,
  delivered early since a typed compile pipeline was needed for Manuscript regardless of export
  format count.
- Command palette fuzzy matching.
- Undo/redo is not yet wired through the manuscript editor at scale; that remains open for a
  future iteration.

## 0.3 Planning

- Story bible / worldbuilding plugin: characters, locations, factions, lore entries as
  entities, linked via relationships.
- Timeline plugin: events as entities, ordered and linked to manuscript scenes and
  story-bible entities.
- Relationship graph visualization as a workspace panel, built purely on the existing
  `Relationship` contract - no new core concept required.
- Expanded shared search covering the new plugins' content.

## 0.4 Publishing

- EPUB and print-ready PDF export, in addition to the plain-text/Markdown/HTML/DOCX export
  already delivered in 0.2.
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
