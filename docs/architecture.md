# Architecture

Skrybe Studio is built around a small, stable **core** and independently developed
**plugins**. This document explains the responsibilities on each side of that line, the shared
contracts that connect them, and why the boundary is enforced the way it is.

## Core vs. plugin responsibilities

The core (`src/skrybe_studio/core/`) provides generic platform services:

| Area | Module | Responsibility |
|---|---|---|
| Entities | `core/entities` | CRUD + soft delete for the shared `Entity` contract |
| Relationships | `core/entities/relationships.py` | Typed connections between entities |
| Events | `core/events` | Synchronous, typed, error-isolated pub/sub |
| Commands | `core/commands` | Registry + dispatch for user/system actions |
| Plugins | `core/plugins` | Manifest validation, discovery, lifecycle |
| Projects | `core/projects` | `.skrybe` create/open/close/validate |
| Storage | `core/storage` | SQLite/SQLAlchemy engine, core tables, migration coordinator |
| Settings | `core/settings` | Application/project/plugin-scoped JSON settings |
| Workspaces | `core/workspaces` | Workspace + panel registration by ID |
| Themes | `core/themes` | Design tokens, light/dark/system resolution |
| Jobs | `core/jobs` | Background work off the Qt main thread, with cancellation |
| Undo | `core/undo` | Qt-free `UndoableCommand` contract over `QUndoStack` |
| Search | `core/search` | Aggregates plugin-registered `SearchProvider`s |
| Services | `core/services` | Typed service locator for cross-plugin interfaces |

**The core never imports anything from `plugins/`.** It has no concept of a "note," an
"asset," a "manuscript," a "timeline," or a "story bible." If you find yourself adding a
feature-specific `if entity_type == "notes.note"` branch inside `core/`, that logic belongs in
a plugin instead.

Everything feature-specific - manuscript writing, story planning, worldbuilding, research,
asset management, timelines, relationship graphs, publishing, and any AI-assisted workflows -
ships as a plugin under `src/skrybe_studio/plugins/`.

## The entity model

Every object a plugin wants to be globally addressable, linkable, or searchable is represented
as an `Entity` (`core/contracts/entity.py`):

```python
class Entity(BaseModel):
    id: UUID
    entity_type: str        # e.g. "notes.note", "assets.asset"
    title: str
    plugin_owner: str        # the plugin's manifest id
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None   # soft delete
    metadata: dict[str, Any]
```

Both reference plugins use the same pattern: the plugin's own primary key **is** the shared
entity ID (a note's `Note.id` and its `Entity.id` are the same UUID). This avoids a second ID
space and makes "is this a valid entity reference" trivially true for anything the plugin
creates. Deletion is soft (`deleted_at`) so relationships and history remain resolvable.

## The relationship model

A `Relationship` (`core/contracts/relationship.py`) is a directed, typed edge between two
entity IDs, owned by whichever plugin created it:

```python
class Relationship(BaseModel):
    id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: str
    plugin_owner: str
    metadata: dict[str, Any]
```

Relationships can cross plugin boundaries freely (e.g. a future timeline event referencing a
character entity owned by a story-bible plugin) without either plugin importing the other -
they only need to know the other's entity ID. This is already exercised for real: Manuscript
creates a `manuscript.cover_asset` relationship pointing at an Asset Library entity for a
manuscript's cover image, and the Asset Library's details panel shows a generic "Linked From"
list for any asset by calling `RelationshipService.for_entity(asset_id)` and looking up the
other side's title through `EntityService` - it never needs to know that `manuscript.cover_asset`
means "this is a cover image" or that Manuscript exists at all, only that *something* points at
this asset. The relationship type string is shown to the user only in a generically humanized
form (last dot-segment, underscores to spaces, title-cased) for exactly this reason.

## The event bus

`core/events/bus.py` provides a synchronous, typed publish/subscribe bus keyed by the
concrete `Event` subclass (not string topics). Each subscriber call is wrapped in its own
`try`/`except`: a raising subscriber is logged and isolated, and can never prevent other
subscribers - or the publisher - from continuing. Subscribe/unsubscribe/publish is the entire
public surface, so a queued or asynchronous implementation could replace the internals later
without changing plugin code.

## Commands

`core/commands/registry.py` is a plain registry keyed by a stable command ID (e.g.
`"notes.new_note"`). A `Command` bundles a title, description, optional shortcut/category/icon,
a zero-argument handler, and an `is_enabled` callback. The main window's menus, toolbar, and
command palette all read from this one registry - they never know which plugin registered a
given command.

## Services (cross-plugin interfaces)

`core/services/container.py` is a typed service locator: a plugin defines a narrow interface
(a `Protocol` or small ABC) for a capability it wants to expose, registers an instance against
that interface type, and other plugins resolve the same interface type. This - along with
entity IDs, events, capability strings in the manifest, and commands - is one of the only ways
plugins are allowed to talk to each other. **Plugins must never import another plugin's
concrete implementation classes.**

Most such interfaces belong in the plugin that defines the capability. The one exception so
far is `AssetLookup` (`core/contracts/asset_lookup.py`): a small `Protocol` (`asset_exists`,
`asset_title`, `resolve_thumbnail`, `list_assets`) that lives in `core/contracts` instead of a
plugin, because it describes a genuinely domain-neutral shape - "resolve an entity ID to
display data" - that any plugin might want to expose or consume, not something specific to
assets. The Asset Library plugin registers an adapter implementing it in `activate()`; the
Manuscript plugin resolves it to optionally show a cover-image thumbnail, and works fully
without it if Asset Library is disabled - resolving the service returns `None` rather than
raising, and callers are expected to treat an absent optional capability as a normal state, not
an error. Adding a new interface to `core/contracts` should be rare and requires the same bar:
the shape must be meaningful with no feature-specific plugin in mind, not just "this happens to
be the second plugin that wants it."

## Workspaces and panels

A `Workspace` (`core/workspaces/models.py`) is a declarative description: a central panel ID,
a set of `(panel_id, dock_area)` placements, and a list of toolbar command IDs - all
**references by string ID**, never by importing a plugin's panel class. The `PanelRegistry`
maps a panel ID to a zero-argument widget factory; the `WorkspaceRegistry` tracks which
workspace is active. The main window (and the standalone plugin host) build their docking
layout purely by resolving IDs through these two registries, so a workspace never needs to
know which plugin implements its panels.

In the full application shell, each registered workspace gets one persistent tab in
`MainWindow`'s tab bar, and each tab's content is a per-workspace `QMainWindow` embedded as a
plain child widget (`setWindowFlags(Qt.WindowType.Widget)` clears the top-level-window flag
`QMainWindow` sets by default) so its own dock widgets stay scoped to that workspace instead of
living directly on the app's real top-level window. Tabs - and their embedded `QMainWindow`
pages - are built once and kept alive for the app's lifetime; only a page's *content* (its
docks and central widget) gets rebuilt, and only when it's stale for the currently open project
(`MainWindow._activate_workspace`, tracked via a per-workspace/per-project "generation" counter).
This means switching between workspaces preserves scroll position, selection, and in-progress
search rather than resetting it - the previous implementation destroyed and rebuilt every panel
on every switch, via a single set of dock widgets shared across all workspaces and a dropdown to
pick which one was live. The standalone plugin host, which only ever shows one workspace, still
docks panels directly on its own top-level `QMainWindow` - there's no nested window there because
there's nothing to switch between.

Per-workspace dock geometry (panel sizes/positions) is **not** persisted across app restarts.
This was attempted via `QMainWindow.saveState()`/`restoreState()` on each embedded workspace
page - the same mechanism the outer window uses for its own geometry - but `restoreState()`
applied to a *non-top-level*, embedded `QMainWindow` produced incorrect dock proportions on the
next launch (a dock could claim most of the window's width instead of its saved share). Dock
sizing resets to each workspace's registration-order default on every app launch instead;
within a single running session, resizing is preserved automatically by the tab-caching
described above (nothing is rebuilt, so nothing is lost) - only surviving a full restart is
unsupported for now.

## Reopening the last project

`Application.reopen_last_project()` reopens whatever project was open when the app last quit,
tracked via a dedicated `last_open_project_path` app setting - deliberately separate from
`RecentProjectsStore`, which keeps history of every project ever opened and exists for the "Open
Recent" menu. `create_project`/`open_project` set it; an explicit `close_project(forget=True)`
(what `MainWindow`'s File > Close Project uses) clears it, while `Application.shutdown()`'s own
internal `close_project()` call - which runs on every quit, project open or not, to deactivate
plugins cleanly - does not, since `forget` defaults to `False`. That distinction is what makes
"quit with a project open" and "explicitly close the project, then quit" behave differently, as
most document-based apps do. If the remembered path no longer resolves to a valid project (moved
or deleted), `reopen_last_project()` clears the setting and returns `None` rather than raising or
retrying on every subsequent launch.

## Cross-cutting UI behavior without core changes

Some plugin UI behavior needs to reach outside the plugin's own panels - Manuscript's focus
mode hides every *other* dock widget in its own workspace; toggling its inspector needs to find
a dock by ID. Rather than adding a manuscript-specific hook to `MainWindow`, this is done through
Qt's own generic widget-tree APIs: `find_enclosing_main_window(self).findChildren(QDockWidget)`
to enumerate every dock in the panel's own enclosing window, and
`find_enclosing_main_window(self).findChild(QDockWidget, "dock.<panel_id>")` to find one by the
same panel ID already used for registration. `find_enclosing_main_window`
(`core/workspaces/panels.py`) walks up to the *nearest* `QMainWindow` ancestor rather than using
`widget.window()`, specifically because of the nested-`QMainWindow`-per-workspace-tab structure
described above: `widget.window()` would resolve past the panel's own workspace to the app's
actual top-level window and search every workspace's docks at once, not just this one's. This
works correctly in both the full application shell (where the nearest ancestor is the panel's own
workspace page) and the standalone plugin host (where it's the same window `widget.window()`
would have found anyway, since the host's `QMainWindow` really is top-level) - and needs zero
further changes to `core/` or `MainWindow` beyond that one helper, so it's a pattern any future
plugin can reuse for similar cross-cutting behavior instead of asking for a new core extension
point.

## Generic contracts introduced for 0.3

0.3 adds a small set of core registries/services to support cross-plugin planning and
story-knowledge features (Story Bible, Relationships, Planning) without any of those plugins
importing one another. Each one follows the same test already applied to `AssetLookup` in 0.2:
would this be useful to a plugin that has nothing to do with story writing? If the honest answer
is "only Story Bible would ever use this," it does not belong here - see, for contrast, the
custom entity-type/field *schema* system, which is Story Bible's own domain model
(`docs/entity-types-and-fields.md`), not a core contract, precisely because nothing outside
Story Bible needs to understand what a "field type" is.

- **`EntityTypeRegistry`** (`core/entities/type_registry.py`) - maps an entity type ID to display
  metadata (`EntityTypeDefinition`: name, plural, icon, capabilities, ...), so any plugin can show
  an icon or label for an entity type it doesn't own (a search result, a backlink row) without
  importing the owning plugin. Exactly the "ID to metadata" shape `PanelRegistry` already uses for
  panels. **Project-scoped** (one fresh instance per open project, in `OpenProject`/
  `ProjectContext`) because project-local custom entity types are project data - a different
  project can have a different set of them - while built-in types are simply re-registered by
  their owning plugin's `activate()` every time a project opens.
- **`RelationshipTypeRegistry`** (`core/entities/relationship_type_registry.py`) - the same idea
  for relationship types (`RelationshipTypeDefinition`: labels, directionality, allowed endpoint
  types, cardinality guidance). Also project-scoped, for the same reason. The canonical
  relationship *records* it describes were already core and already generic
  (see "The relationship model" above) - this only adds a place to describe what a relationship
  *type* means for display and validation, which no plugin defining a type should have to
  re-explain to every other plugin that might render one.
- **`EntityViewerRegistry`** (`core/navigation/viewer_registry.py`) - maps an entity type's
  namespace (the text before its first ".", e.g. "story_bible", "manuscript") to a reveal handler
  - a bound method on the owning plugin instance that shows/focuses a given entity ID, exactly
  like a `Command.is_enabled` callback: expected to check its own plugin's state and no-op
  gracefully rather than raise. Registered once per namespace at `register()` time, since
  namespaces are static even though the individual (possibly custom, possibly project-local)
  entity types within one are not. **App-wide** (`PluginContext`), matching `PanelRegistry`.
- **`NavigationService`** (`core/navigation/service.py`) + **`NavigationTarget`**
  (`core/contracts/navigation.py`) - a Qt-free Back/Forward history over entity IDs, promoting the
  exact shape Manuscript's own (unchanged) intra-document `NavigationHistory` already used in 0.2,
  so history can span plugin boundaries. It only tracks a position in a list; it does not know
  `EntityViewerRegistry` exists - whatever wires up a global "Back" action is responsible for
  taking `go_back()`'s result and calling `EntityViewerRegistry.reveal()` itself. **App-wide**, but
  `Application.create_project`/`open_project`/`close_project` all call `navigation.clear()`, since
  entity IDs from a different (or no) project are meaningless.
- **`IssueService`** (`core/issues/service.py`) + **`Issue`/`IssueProvider`**
  (`core/issues/contracts.py`) - a small aggregator for deterministic integrity issues
  ("a relationship points at an archived entity"), deliberately mirroring `SearchService`/
  `SearchProvider`: ask every registered plugin for typed contributions, tolerate any one raising,
  know nothing about what the contributions mean. This is the entire "continuity foundation" -
  not a continuity checker. The actual rule logic lives entirely in whichever plugin can evaluate
  it (Story Bible, Planning); core only standardizes the shape of the result.

None of the above required touching `Workspace`/`PanelRegistry` (workspaces already register
generically, per "Workspaces and panels"), and none of them added anything domain-specific to
`core/` - the encyclopedia of *what kinds of things* exist (character, location, "knows",
"parent of", ...) is entirely Story Bible's own data, described in
[`docs/entity-types-and-fields.md`](entity-types-and-fields.md).

## Storage ownership

Each project is one SQLite file (`project.db`). Core-owned tables (`core_entities`,
`core_relationships`, `core_plugin_migrations`) live under `core/storage/models.py`, using the
core's own `DeclarativeBase` (`core/storage/base.py`). Every plugin defines **its own**
`DeclarativeBase` (e.g. `NotesBase`, `AssetsBase`) for its own tables - multiple declarative
bases can safely target the same SQLAlchemy `Engine`/SQLite file as long as table names don't
collide (by convention, plugin tables are prefixed with the plugin's short name:
`notes_note`, `assets_asset`).

`core/storage/database.py` wraps the engine/session with foreign keys enabled and explicit
commit/rollback transaction boundaries (`Database.session()` is a context manager). No widget
ever touches SQLAlchemy directly - persistence always goes through a plugin's
repository/service layer.

## Migration ownership

Full Alembic integration is deferred for this iteration in favor of a small, testable
`PluginMigrationCoordinator` (`core/storage/migration_coordinator.py`). A plugin supplies an
ordered list of named `Migration`s (each just a `(name, apply(engine))` pair); the coordinator
tracks which migration names have already run per plugin ID in the `core_plugin_migrations`
ledger table, so migrations only run once, only for plugins that are actually loaded, and a
failure raises a clear `MigrationError` naming the plugin and migration rather than silently
corrupting state.

## Error isolation

Isolation happens at three layers:

1. **Event subscribers** - one subscriber raising never stops another, or the publisher
   (`EventBus.publish`).
2. **Plugin loading** - an invalid manifest, unsupported API version, missing/circular
   dependency, or entrypoint import failure is collected as a `PluginLoadFailure` rather than
   raised; `PluginLoader.discover_and_instantiate` never lets one broken plugin prevent
   others - or the application - from starting.
3. **Plugin lifecycle calls** - `Application` (`app/bootstrap.py`) wraps every
   `register`/`activate`/`deactivate`/`shutdown` call in its own `try`/`except`, logging and
   continuing rather than propagating.

Unhandled exceptions that do escape all of that are caught by the top-level excepthook
(`core/errors.py`), logged, and shown to the user via a plain-language dialog with a
copyable "Show Details" section - never a raw traceback as the primary message.

## Why plugins must not import one another directly

If plugin A imports a concrete class from plugin B, disabling or failing to load B silently
breaks A in a way the loader's isolation cannot catch (the failure happens at Python import
time, inside A's own module, often far from any log message that identifies B as the cause).
It also makes the two plugins impossible to test, version, or ship independently - the entire
point of the plugin architecture. Every legitimate cross-plugin interaction has a purpose-built
channel that keeps the failure isolated to whichever plugin actually breaks:

- **Entity IDs** - reference another plugin's data without knowing its schema.
- **Events** - react to another plugin's state changes without a direct call.
- **Service interfaces** (`core/services`) - consume a capability through a shared `Protocol`.
- **Capability registration** (manifest `capabilities`) - advertise what a plugin provides.
- **Commands** - trigger another plugin's action by stable ID, not by function reference.
