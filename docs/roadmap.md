# Roadmap

Skrybe Studio is being built in broad phases. **0.1 Platform** and **0.2 Writing** are
delivered; everything after them is directional, not committed or scheduled.

## Branch status (as of 0.3 development start)

`main` does not yet contain 0.2 - `feat/manuscript-v0.2` (13 commits ahead of `main`) is
complete, quality-gated, and unmerged, unpushed, and untagged by explicit instruction. 0.3
development (`feat/story-knowledge-v0.3`) is **stacked on `feat/manuscript-v0.2`**, not on
`main`, because 0.3's Story Bible/Relationships/Planning plugins depend on 0.2's Manuscript
plugin, `AssetLookup` contract, tab-based workspace switching, and reopen-last-project behavior
- none of which exist on `main` yet. Merging 0.3 to `main` will require `feat/manuscript-v0.2`
to land first (or `feat/story-knowledge-v0.3` to be rebased onto `main` after that merge,
replaying its commits against the 0.2 work already merged in). Nothing has been pushed, merged,
or tagged as of this note.

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

## 0.3 Planning and Story Knowledge (in progress)

- **Story Bible** plugin: knowledge entities (characters, locations, organizations, items, and
  other built-in and user-defined types), a project-local custom entity-type and custom-field
  system, entity-to-entity and entity-to-manuscript-scene relationships, backlinks, and a
  dedicated Worldbuilding workspace.
- **Relationships** plugin: a graph visualization over the shared `Relationship` contract
  (pan/zoom/filter/layout/saved views) that owns only presentation state - graph nodes display
  canonical entities, never a duplicate copy of their data.
- **Planning** plugin: corkboard and beat-board views over Manuscript's existing scene entities
  (referenced by ID, never duplicated), plot threads, structure templates, and a clearly
  separated Planning Order vs. Manuscript Order so rearranging cards during planning can never
  silently reorder the manuscript.
- Explicit, rename-safe entity links insertable into manuscript content (`skrybe://entity/<uuid>`
  or an equivalent stable-ID scheme), surviving autosave, snapshots, and export.
- A small generic issue-reporting foundation and a handful of deterministic integrity checks
  (e.g. a relationship pointing at an archived entity) - not a full continuity checker.
- Expanded shared search and cross-plugin navigation (Back/Forward, reveal) covering all of the
  above, with every plugin remaining independently disable-able without corrupting or losing
  the others' data.
- See [`docs/story-bible-plugin.md`](story-bible-plugin.md),
  [`docs/relationships-plugin.md`](relationships-plugin.md),
  [`docs/planning-plugin.md`](planning-plugin.md),
  [`docs/entity-types-and-fields.md`](entity-types-and-fields.md), and
  [`docs/entity-linking.md`](entity-linking.md) for design detail as each lands.

Explicitly out of scope for 0.3 (deferred, not designed against yet): a timeline/fictional-
calendar engine, a full continuity checker (0.3 ships only a small deterministic-issue
foundation), a full revision dashboard, EPUB/print publishing, an AI assistant, cloud sync,
real-time collaboration, a plugin marketplace, mobile apps, submission tracking, a general
custom-database/query-builder product, a geographic map editor, a whiteboard system, or a full
mind-mapping clone. The Relationships plugin's graph canvas is a focused, native-Qt
visualization over existing entities/relationships - not a universal infinite-canvas platform.

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
