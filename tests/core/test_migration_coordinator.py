from __future__ import annotations

from pathlib import Path

import pytest

from skrybe_studio.core.storage.database import Database
from skrybe_studio.core.storage.migration_coordinator import (
    Migration,
    MigrationError,
    PluginMigrationCoordinator,
)


def _database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "project.db")
    database.create_core_tables()
    return database


def test_migration_applies_once(tmp_path: Path) -> None:
    database = _database(tmp_path)
    coordinator = PluginMigrationCoordinator(database)
    calls: list[str] = []

    migration = Migration(name="0001_initial", apply=lambda engine: calls.append("applied"))

    applied_first = coordinator.apply("plugin.a", [migration])
    applied_second = coordinator.apply("plugin.a", [migration])

    assert applied_first == ["0001_initial"]
    assert applied_second == []
    assert calls == ["applied"]


def test_migrations_are_scoped_per_plugin(tmp_path: Path) -> None:
    database = _database(tmp_path)
    coordinator = PluginMigrationCoordinator(database)
    migration = Migration(name="0001_initial", apply=lambda engine: None)

    coordinator.apply("plugin.a", [migration])
    applied_for_b = coordinator.apply("plugin.b", [migration])

    assert applied_for_b == ["0001_initial"]


def test_failing_migration_raises_migration_error(tmp_path: Path) -> None:
    database = _database(tmp_path)
    coordinator = PluginMigrationCoordinator(database)

    def _boom(engine: object) -> None:
        raise RuntimeError("schema error")

    migration = Migration(name="0001_initial", apply=_boom)

    with pytest.raises(MigrationError):
        coordinator.apply("plugin.a", [migration])

    assert coordinator.applied_migrations("plugin.a") == set()
