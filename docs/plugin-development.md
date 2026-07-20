# Plugin Development

This guide walks through building a Skrybe Studio plugin, using the Notes plugin
(`src/skrybe_studio/plugins/notes/`) as the running example. Read
[`docs/architecture.md`](architecture.md) first - it explains *why* the rules below exist.

## Directory structure

```text
plugins/<name>/
├── application/     # services orchestrating domain + persistence + entities + events
├── domain/           # plain Python domain model - no Qt, no SQLAlchemy
├── infrastructure/   # SQLAlchemy models (own DeclarativeBase) + repository
├── migrations/       # named Migration list for the PluginMigrationCoordinator
├── resources/         # icons, static assets shipped with the plugin
├── ui/                 # Qt Widgets panels
├── manifest.json
└── plugin.py           # the Plugin entrypoint class
```

This is a plain layered architecture: `ui` depends on `application`, `application` depends on
`domain` + `infrastructure`, `infrastructure` depends on `domain`. Nothing outside the plugin's
own directory is allowed to depend on anything but the plugin's `plugin.py` entrypoint and its
manifest's declared `capabilities`.

## The manifest

`manifest.json` is validated against `PluginManifest`
(`core/plugins/manifest.py`) at discovery time:

```json
{
  "id": "com.adeptus-craftmatica.skrybe.notes",
  "name": "Notes",
  "version": "0.1.0",
  "api_version": "1",
  "description": "Create and organize project notes.",
  "author": "adeptus-craftmatica",
  "entrypoint": "skrybe_studio.plugins.notes.plugin:NotesPlugin",
  "capabilities": ["workspace.panel", "entity.provider", "command.provider", "search.provider"],
  "requires": [],
  "optional_requires": []
}
```

- `id` should be a reverse-DNS-style string; it is also the value stored as `plugin_owner` on
  every `Entity`/`Relationship` the plugin creates.
- `entrypoint` is `"module.path:ClassName"` - a class implementing the `Plugin` ABC.
- `requires` / `optional_requires` list other plugin IDs; the loader topologically sorts by
  `requires` and fails the dependent (not the whole app) if a required dependency is missing
  or the graph has a cycle.
- **Convention for standalone execution**: the plugin's primary `Workspace.id` should be the
  last dot-segment of its manifest `id` (e.g. `...skrybe.notes` -> workspace id `"notes"`) so
  the plugin host (see below) can find it without any plugin-specific code.

## Lifecycle

```python
class Plugin(ABC):
    @abstractmethod
    def register(self, context: PluginContext) -> None: ...
    def activate(self, context: ProjectContext) -> None: ...
    def deactivate(self, context: ProjectContext) -> None: ...
    def shutdown(self, context: PluginContext) -> None: ...
```

- **`register(PluginContext)`** runs once at application startup, before any project is open.
  `PluginContext` carries only app-wide services: `events`, `commands`, `settings`,
  `workspaces`, `panels`, `services`, `jobs`, `search`. Register panels, workspaces, and
  commands here.
- **`activate(ProjectContext)`** runs every time a project opens. `ProjectContext` carries
  project-scoped services that don't exist before then: `entities`, `relationships`,
  `database`, `migrations`. Build your repository and application service here, and apply
  your migrations.
- **`deactivate(ProjectContext)`** runs when the project closes - release anything you built in
  `activate` (set your service reference back to `None`, unregister search providers, etc.).
- **`shutdown(PluginContext)`** runs once at application exit.

A plugin that raises inside any of these is logged and isolated by `Application`
(`app/bootstrap.py`) - it does not take down the rest of the app.

## Registering panels

```python
context.panels.register("notes.browser", "Notes", lambda: NotesBrowserPanel(self, context.events))
```

Panels are looked up by ID everywhere else in the application (main window, standalone host) -
never imported directly by workspace code.

## Registering a workspace

```python
context.workspaces.register(
    Workspace(
        id="notes",
        title="Notes",
        central_panel_id="notes.editor",
        panels=(PanelPlacement(panel_id="notes.browser", area="left"),),
    )
)
```

## Registering commands

```python
context.commands.register(
    Command(
        id="notes.new_note",
        title="New Note",
        shortcut="Ctrl+Shift+N",
        category="Notes",
        handler=self._create_note,
        is_enabled=lambda: self.service is not None,
    )
)
```

Commands show up in the menu bar structure a workspace contributes and in the command
palette automatically - nothing else needs to change.

## Publishing and subscribing to events

Define typed events as `Event` subclasses:

```python
@dataclass(frozen=True, slots=True)
class NoteCreated(Event):
    note_id: UUID
    title: str
```

Publish from your application service after a state change commits:

```python
self._events.publish(NoteCreated(note_id=note.id, title=note.title))
```

Subscribe from a panel (or another plugin) by the concrete class:

```python
events.subscribe(NoteCreated, self._on_note_changed)
```

A subscriber that raises is logged and isolated - it never breaks the publisher or other
subscribers.

## Creating entities

Give your domain object's primary key double duty as the shared entity ID:

```python
self._entities.create(
    entity_type="notes.note",
    title=title,
    plugin_owner=PLUGIN_ID,
    entity_id=note_id,   # same UUID as your own row's primary key
)
```

Use `entities.rename()` when your title changes, and `entities.soft_delete()` when your record
is deleted, so the shared entity stays in sync.

## Adding tables and a migration

1. Define your own `DeclarativeBase` subclass (do **not** import the core's `Base`):

   ```python
   class NotesBase(DeclarativeBase):
       pass

   class NoteRecord(NotesBase):
       __tablename__ = "notes_note"
       ...
   ```

2. Provide a migration list in `migrations/__init__.py`:

   ```python
   def _create_initial_schema(engine: Engine) -> None:
       NotesBase.metadata.create_all(engine)

   def get_migrations() -> list[Migration]:
       return [Migration(name="0001_initial_schema", apply=_create_initial_schema)]
   ```

3. Apply it in `activate()`:

   ```python
   context.migrations.apply(PLUGIN_ID, get_migrations())
   ```

The coordinator records applied migration names per plugin ID, so this is safe to call on
every activation - already-applied migrations are skipped.

## Contributing search results

Implement the `SearchProvider` protocol (just a `search(query) -> list[SearchResult]` method)
and register it in `activate()`:

```python
self._search_provider = NotesSearchProvider(repository)
context.search.register_provider(self._search_provider)
```

Unregister it in `deactivate()` via `context.search.unregister_provider(...)`.

## Contributing an undoable action

Implement the plain `UndoableCommand` protocol (`description`, `do()`, `undo()` - no Qt
import required) and push it onto a `UndoService`:

```python
@dataclass
class RenameNoteCommand:
    description: str
    _service: NotesService
    _note_id: UUID
    _old_title: str
    _new_title: str

    def do(self) -> None:
        self._service.rename_note(self._note_id, self._new_title)

    def undo(self) -> None:
        self._service.rename_note(self._note_id, self._old_title)
```

## Running a plugin standalone

```bash
uv run python -m skrybe_studio.plugin_host --plugin notes
```

The host loads every plugin (so `requires` dependencies still resolve), opens a persistent
per-plugin development project under the application data directory, and renders only the
requested plugin's workspace - found by the naming convention above. No full application shell,
menus, or other plugins' UI are shown.

## Testing plugins

- Domain and application-layer tests should construct a `Database` pointed at `tmp_path`,
  call `YourPluginBase.metadata.create_all(database.engine)` directly (skip the migration
  coordinator for unit tests), and exercise your service against real `EntityService`/
  `EventBus` instances - see `tests/plugins/notes/test_notes_service.py` for the pattern.
- UI panels can be tested with `pytest-qt`'s `qtbot` fixture.
- Never write test fixtures into the real user home, app-support, or log directories - use
  `tmp_path` and the isolated `application`/`app_paths` fixtures in `tests/conftest.py`.
