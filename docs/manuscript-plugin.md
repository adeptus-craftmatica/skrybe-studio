# The Manuscript Plugin

The Manuscript plugin (`com.adeptus-craftmatica.skrybe.manuscript`,
`src/skrybe_studio/plugins/manuscript/`) is the first major creative-domain plugin built on top
of the v0.1 platform. It follows every rule in
[`docs/plugin-development.md`](plugin-development.md) - core stays manuscript-unaware, and every
cross-plugin interaction goes through entity IDs, events, service interfaces, capabilities, or
commands. This document explains the domain rules and design decisions specific to Manuscript
that a general plugin-development guide shouldn't have to cover.

## Directory layout

```text
plugins/manuscript/
├── domain/          # ManuscriptNode, hierarchy validation, document IR, word counting
├── infrastructure/   # SQLAlchemy models + ManuscriptRepository/SnapshotRepository/ProgressRepository
├── migrations/        # 0001_initial_schema
├── application/         # HierarchyService, DocumentService, SnapshotService, GoalsService,
│                          NavigationHistory, ManuscriptSearchProvider, ManuscriptAssetService,
│                          export/ (compile pipeline + exporters)
├── ui/                    # binder/, editor/, inspector/, search_panel.py, dialogs/
├── manifest.json
└── plugin.py                # ~20 commands, 4 panels, 1 workspace ("Writing")
```

Unlike Notes and Asset Library, `ManuscriptPlugin` exposes one named attribute per concern
(`self.hierarchy`, `self.documents`, `self.snapshots`, `self.goals`, `self.assets`,
`self.search_provider`, `self.navigation`) instead of a single `self.service` - see
[`docs/plugin-development.md`](plugin-development.md#directory-structure) for when that split
makes sense.

## Hierarchy model

A manuscript is a tree of `ManuscriptNode`s (`domain/models.py`), all sharing one table
(`manuscript_node`) and one entity-type family. `ManuscriptNodeType`
(`domain/enums.py`) is `MANUSCRIPT | FOLDER | PART | CHAPTER | SCENE | DOCUMENT`; only
`SCENE` and `DOCUMENT` are text-bearing (`TEXT_BEARING_NODE_TYPES`) - they're the only node
types with a row in `manuscript_document_content`. `ALLOWED_CHILD_TYPES` defines which types
may parent which; `HierarchyService.move_node()`/`create_node()` check it via
`validate_child_type()` and reject the move/creation with `InvalidHierarchyError` otherwise.

A node's archival state is `archived_at: datetime | None`, deliberately **not** folded into
`NodeStatus` (`PLANNED | DRAFT | REVISED | FINAL`) - a scene can be `FINAL` and archived at the
same time; those are two independent facts, not points on one enum.

Moving a node also checks for cycles via `would_create_cycle()` (a pure function taking a
`get_parent_id` callable, so it's unit-testable without a database) and raises
`CyclicHierarchyError`. Sort order between siblings uses fractional keys
(`sort_order_between()`, `infrastructure/repositories.py`) so reordering one node is an O(1)
single-row update, never a bulk renumbering of siblings.

Archiving cascades to descendants and is reversible (`archive_node()`/`restore_node()` both
return the full set of affected node IDs). Duplication (`duplicate_node()`) is shallow by
design - it copies a node's own content but not its descendants, matching what "duplicate this
chapter" usually means to a writer (a fresh chapter to fill in, not a full subtree clone).

## Document content

Document text is Qt-free: `DocumentBlock`/`TextSpan`/`BlockKind` tuples (`domain/document_ir.py`),
JSON-serialized into `manuscript_document_content.content_json`. The editor bridges this IR to a
`QTextDocument` (`ui/editor/text_bridge.py`) using a **documented heuristic**, not a rich
round-trip format: heading blocks are recognized by point size, blockquotes by left margin. This
keeps the domain model reusable by non-Qt code (exporters, tests, a future different UI) at the
cost of the editor only supporting the small set of styles the heuristic knows about
(paragraph/heading/blockquote, bold/italic/underline spans).

Saving content (`DocumentService.save_content()`) recomputes the node's cached `word_count`,
records the day's net word-count delta (for writing goals), and publishes
`DocumentContentChanged` - all in one call, so nothing else has to remember to keep the cache or
goal tracking in sync.

## Editor behavior

`EditorPanel` (`ui/editor/editor_panel.py`) manages two independent tab widgets
(`_primary_tabs`/`_secondary_tabs`) for the optional split view, debounced autosave
(`DocumentEditor.AUTOSAVE_DELAY_MS = 800`), and an explicit `flush()`/`flush_all()` path for
save points that can't wait for the debounce (closing a tab, compiling, switching projects).
Typewriter scrolling's target-offset math (`ui/editor/typewriter.py`) is a pure function with no
widget dependency, so it's tested without a `QTextEdit` at all.

Focus mode and the inspector-toggle command don't reach into `MainWindow` - they use
`self.window().findChildren(QDockWidget)` / `findChild(QDockWidget, "dock.manuscript.inspector")`
to find dock widgets generically by the same panel ID already used at registration time. See
[`docs/architecture.md`](architecture.md#cross-cutting-ui-behavior-without-core-changes) for why
this avoids adding a manuscript-specific hook to core UI.

## Navigation history

`NavigationHistory` (`application/navigation.py`) only records **text-bearing** node visits -
opening a folder or part in the binder doesn't push a history entry, matching "Back/Forward"
semantics writers expect from a recent-documents list, not a full tree-selection history.
Because the binder can also open a document indirectly (revealing a search result, following a
link), the editor checks a single `ManuscriptPlugin.suppress_navigation_recording` flag inside
`_record_navigation()` rather than each call site tracking its own local suppression state -
this was a deliberate fix during development after direct calls and event-bus-triggered opens
turned out to double-record the same visit.

## Snapshots

`SnapshotService.restore_snapshot()` always takes a **safety snapshot first**
(`SAFETY_SNAPSHOT_NAME = "Before restore"`) before overwriting current content, so a restore is
itself undoable by restoring again. Diffing (`application/diff.py`) uses stdlib `difflib` against
plain text, not a real text-merge algorithm - sufficient for "what changed since this snapshot,"
not intended as a version-control replacement.

## Writing goals

Per-node word-count targets live directly on `ManuscriptNode.target_word_count` (nullable - a
target is optional, and clearing it back to `None` is a real, distinct operation from setting it
to `0`, hence `HierarchyService.set_target_word_count()` is a dedicated setter rather than
folded into general metadata update). The daily target is a manuscript-level setting stored in
the root node's `metadata` dict; daily progress (net word delta per day) accumulates in
`manuscript_daily_progress`, upserted by `ProgressRepository.record_delta()` every time
`DocumentService.save_content()` runs.

## Search and compile share one traversal shape

Both `ManuscriptSearchProvider` and `Compiler` (`application/export/compile.py`) walk the same
hierarchy, but for different purposes: search matches title/synopsis/tags/body text across the
whole tree or a scoped subtree; compile produces an ordered, typed `CompileDocument` tree
respecting `include_in_compile` and archival state, deterministically (same input always
produces the same section order), which every exporter (`export/plain_text.py`, `markdown.py`,
`html.py`, `docx_exporter.py`) then renders independently from the same `CompileDocument` - no
exporter talks to the database or the hierarchy service directly.

## Why export splits compile from write

`Compiler.compile()` reads the database (fast, synchronous, must run on the Qt main thread since
SQLite connections aren't thread-safe). The actual file write is DB-free once it has a
`CompileDocument` in hand, so `ExportService.export()` runs *only that step* as a background
`Job` (`export/service.py`) - the UI stays responsive during a DOCX write on a large manuscript
without needing any manuscript-specific threading code beyond the existing `core/jobs`
abstraction.

## Optional asset integration

Manuscript's only dependency on another plugin is a manuscript-root cover image, resolved
through the `AssetLookup` capability (see
[`docs/architecture.md`](architecture.md#services-cross-plugin-interfaces) and
[`docs/plugin-development.md`](plugin-development.md#consuming-another-plugins-optional-capability)).
`ManuscriptAssetService` (`application/asset_integration.py`) treats an unavailable capability as
a normal state: the inspector shows "Asset Library unavailable" instead of the cover-image
section failing or the plugin refusing to load. Manuscript's own tests and the app itself work
identically whether Asset Library is enabled, disabled, or was never installed.

## Explicitly out of scope for v0.2

Story bible, timeline, relationship graph visualization, an AI writing assistant, cloud sync,
EPUB, and print-ready PDF are not part of this plugin - see
[`docs/roadmap.md`](roadmap.md) for where (if anywhere) they're planned.

## Testing

`tests/plugins/manuscript/` mirrors the plugin's own layers (domain, repository, each
application service, the binder's Qt model, export) using the same pattern as the Notes plugin's
tests: point a `Database` at `tmp_path`, call `ManuscriptBase.metadata.create_all()` directly
(skipping the migration coordinator), and exercise real `HierarchyService`/`EventBus` instances
rather than mocks. `tests/integration/test_manuscript_integration.py` covers the full-app golden
path (create → write → close → reopen), v0.1 project compatibility, standalone plugin host
execution, and Asset Library graceful degradation.
