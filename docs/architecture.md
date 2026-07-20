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
they only need to know the other's entity ID.

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

## Workspaces and panels

A `Workspace` (`core/workspaces/models.py`) is a declarative description: a central panel ID,
a set of `(panel_id, dock_area)` placements, and a list of toolbar command IDs - all
**references by string ID**, never by importing a plugin's panel class. The `PanelRegistry`
maps a panel ID to a zero-argument widget factory; the `WorkspaceRegistry` tracks which
workspace is active. The main window (and the standalone plugin host) build their docking
layout purely by resolving IDs through these two registries, so a workspace never needs to
know which plugin implements its panels.

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
