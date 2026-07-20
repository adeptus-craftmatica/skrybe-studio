"""Manuscript plugin migrations, applied by the core's `PluginMigrationCoordinator`."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from skrybe_studio.core.storage.migration_coordinator import Migration
from skrybe_studio.plugins.manuscript.infrastructure.models import ManuscriptBase


def _create_initial_schema(engine: Engine) -> None:
    ManuscriptBase.metadata.create_all(engine)


def get_migrations() -> list[Migration]:
    return [Migration(name="0001_initial_schema", apply=_create_initial_schema)]
