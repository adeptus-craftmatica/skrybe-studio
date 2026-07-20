"""Settings service exposing application, project, and plugin scopes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from skrybe_studio.core.settings.store import JsonSettingsStore


class SettingsService:
    """Composes the application-wide store with the current project's store.

    Application scope always exists. Project scope is attached when a
    project opens and detached when it closes; reads against project
    scope with no project open simply return the provided default.
    """

    def __init__(self, application_settings_path: Path) -> None:
        self._app_store = JsonSettingsStore(application_settings_path)
        self._project_store: JsonSettingsStore | None = None

    def attach_project(self, project_settings_path: Path) -> None:
        self._project_store = JsonSettingsStore(project_settings_path)

    def detach_project(self) -> None:
        self._project_store = None

    # --- application scope -------------------------------------------------

    def get_app(self, key: str, default: Any = None) -> Any:
        return self._app_store.get(key, default)

    def set_app(self, key: str, value: Any) -> None:
        self._app_store.set(key, value)

    # --- project scope -------------------------------------------------

    def get_project(self, key: str, default: Any = None) -> Any:
        if self._project_store is None:
            return default
        return self._project_store.get(key, default)

    def set_project(self, key: str, value: Any) -> None:
        if self._project_store is None:
            raise RuntimeError("No project is open; cannot write project-scoped settings")
        self._project_store.set(key, value)

    @property
    def has_project(self) -> bool:
        return self._project_store is not None

    # --- plugin scope (nested under either application or project scope) --

    def get_plugin(
        self, plugin_id: str, key: str, default: Any = None, *, project_scope: bool = False
    ) -> Any:
        full_key = f"plugins.{plugin_id}.{key}"
        return (
            self.get_project(full_key, default)
            if project_scope
            else self.get_app(full_key, default)
        )

    def set_plugin(
        self, plugin_id: str, key: str, value: Any, *, project_scope: bool = False
    ) -> None:
        full_key = f"plugins.{plugin_id}.{key}"
        if project_scope:
            self.set_project(full_key, value)
        else:
            self.set_app(full_key, value)
