from __future__ import annotations

from pathlib import Path

import pytest

from skrybe_studio.core.settings.service import SettingsService
from skrybe_studio.core.settings.store import JsonSettingsStore


def test_json_store_round_trips_through_disk(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    store = JsonSettingsStore(path)
    store.set("theme", "dark")
    store.set("window.geometry", "abc123")

    reloaded = JsonSettingsStore(path)

    assert reloaded.get("theme") == "dark"
    assert reloaded.get("window.geometry") == "abc123"
    assert reloaded.get("missing.key", "fallback") == "fallback"


def test_app_scope_persists(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "app.json")
    service.set_app("theme", "dark")

    assert service.get_app("theme") == "dark"
    assert SettingsService(tmp_path / "app.json").get_app("theme") == "dark"


def test_project_scope_requires_attached_project(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "app.json")

    assert service.has_project is False
    assert service.get_project("last_workspace", "default") == "default"
    with pytest.raises(RuntimeError):
        service.set_project("last_workspace", "notes")


def test_project_scope_after_attach(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "app.json")
    service.attach_project(tmp_path / "project-settings.json")

    service.set_project("last_workspace", "notes")

    assert service.get_project("last_workspace") == "notes"

    service.detach_project()
    assert service.has_project is False


def test_plugin_scope_nests_under_plugin_id(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "app.json")

    service.set_plugin("com.example.notes", "thumbnail_size", 128)

    assert service.get_plugin("com.example.notes", "thumbnail_size") == 128
    assert service.get_app("plugins.com.example.notes.thumbnail_size") == 128
