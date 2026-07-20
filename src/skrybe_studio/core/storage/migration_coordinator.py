"""Custom, testable coordinator for plugin-owned schema migrations.

Full Alembic integration is deferred; for this iteration each plugin
supplies an ordered list of named `Migration`s (typically one "initial
schema" migration that calls `Base.metadata.create_all` for its own
declarative base). The coordinator tracks which migrations have already
been applied per plugin so migrations only run for installed, enabled
plugins and never re-run.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.engine import Engine

from skrybe_studio.core.storage.database import Database
from skrybe_studio.core.storage.models import PluginMigrationRecord

logger = logging.getLogger(__name__)


class MigrationError(RuntimeError):
    """Raised when a plugin migration fails to apply."""


@dataclass(frozen=True, slots=True)
class Migration:
    """A single named, idempotent-once-applied plugin migration step."""

    name: str
    apply: Callable[[Engine], None]


class PluginMigrationCoordinator:
    """Applies plugin-owned schema migrations against the project database."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def applied_migrations(self, plugin_id: str) -> set[str]:
        with self._database.session() as session:
            rows = session.scalars(
                select(PluginMigrationRecord.migration_name).where(
                    PluginMigrationRecord.plugin_id == plugin_id
                )
            )
            return set(rows)

    def apply(self, plugin_id: str, migrations: Iterable[Migration]) -> list[str]:
        """Apply any not-yet-applied migrations for a plugin, in order.

        Returns the names of migrations newly applied during this call.
        """
        already_applied = self.applied_migrations(plugin_id)
        applied_now: list[str] = []
        for migration in migrations:
            if migration.name in already_applied:
                continue
            try:
                migration.apply(self._database.engine)
            except Exception as exc:
                raise MigrationError(
                    f"Migration '{migration.name}' failed for plugin '{plugin_id}': {exc}"
                ) from exc
            with self._database.session() as session:
                session.add(
                    PluginMigrationRecord(
                        plugin_id=plugin_id,
                        migration_name=migration.name,
                        applied_at=datetime.now(UTC),
                    )
                )
            applied_now.append(migration.name)
            logger.info("Applied migration '%s' for plugin '%s'", migration.name, plugin_id)
        return applied_now
