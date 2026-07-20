# Project Format

A Skrybe Studio project is a directory ending in `.skrybe`:

```text
MyNovel.skrybe/
├── project.db        # entities, relationships, plugin state, notes, asset metadata (SQLite)
├── project.json       # lightweight project metadata only
├── documents/          # reserved for future manuscript/document plugins
├── assets/              # imported asset files, UUID-based filenames
├── exports/             # reserved for future publishing/export plugins
├── cache/                # thumbnails and other regenerable, non-canonical data
│   ├── thumbnails/
│   └── project-settings.json   # project-scoped settings (window/workspace state, etc.)
└── backups/               # reserved for future backup coordination
```

## `project.json`

Deliberately small - only what's needed to identify and validate the project, never a
catch-all document:

```json
{
  "id": "5b1e...-uuid",
  "name": "My Novel",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z",
  "app_version": "0.1.0",
  "format_version": 1,
  "enabled_plugins": []
}
```

Validated against `ProjectMetadata` (`core/projects/models.py`) on open.

## `project.db`

A single SQLite file, opened with `PRAGMA foreign_keys=ON`. Core-owned tables:

- `core_entities` - every shared `Entity`, across every plugin.
- `core_relationships` - every shared `Relationship`.
- `core_plugin_migrations` - the migration ledger (which named migration ran for which plugin).

Plugin-owned tables live in the same file, prefixed by plugin name (`notes_note`,
`assets_asset`, `manuscript_node`, `manuscript_document_content`, `manuscript_snapshot`,
`manuscript_daily_progress`, ...), each defined against the plugin's own `DeclarativeBase`. See
[`docs/architecture.md`](architecture.md#storage-ownership) for why this is safe.

## `assets/`

Imported files are copied here under a **content-safe, UUID-based filename**
(`<asset-id><original-extension>`) - never the original filename, and never referenced by
absolute external path. The original filename is preserved separately in `assets_asset.
original_filename` for display. This means:

- Renaming or moving the source file after import has no effect on the project.
- Two different projects can safely have files with the same original name.
- The canonical reference stored anywhere in the database is always the asset's UUID, never a
  filesystem path.

## `cache/`

Regenerable, non-canonical data: asset thumbnails (`cache/thumbnails/<asset-id>.png`) and
project-scoped settings (`cache/project-settings.json`). Nothing here is required to
reconstruct the project - it can be deleted and will be regenerated or fall back to defaults.

## `documents/`, `exports/`, `backups/`

Still reserved and unused as of v0.2.0. The Manuscript plugin does **not** store document
content as files under `documents/` - scene/document text lives in `manuscript_document_content`
alongside every other manuscript table in `project.db`, so a manuscript node's content is
covered by the same soft-deletion, migration, and single-file-backup story as everything else
in the database. Exported files (plain text/Markdown/HTML/DOCX) are written to whatever path
the user picks in the export dialog's save-file prompt, not automatically into `exports/`.
`backups/` remains reserved for the backup coordination described in
[`docs/roadmap.md`](roadmap.md). No archive compression is implemented yet.

## Recently opened projects

Tracked in application-scoped settings (`RecentProjectsStore`, `core/projects/recent.py`), not
inside any project directory - a list of `{path, name, last_opened}` entries, most recent
first, capped at 10.
