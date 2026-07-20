"""Registers workspaces and tracks which one is active."""

from __future__ import annotations

import logging

from skrybe_studio.core.workspaces.models import Workspace

logger = logging.getLogger(__name__)


class DuplicateWorkspaceError(RuntimeError):
    """Raised when two workspaces are registered under the same ID."""


class WorkspaceRegistry:
    def __init__(self) -> None:
        self._workspaces: dict[str, Workspace] = {}
        self._active_id: str | None = None

    def register(self, workspace: Workspace) -> None:
        if workspace.id in self._workspaces:
            raise DuplicateWorkspaceError(f"Workspace '{workspace.id}' is already registered")
        self._workspaces[workspace.id] = workspace
        if self._active_id is None:
            self._active_id = workspace.id
        logger.debug("Registered workspace '%s'", workspace.id)

    def get(self, workspace_id: str) -> Workspace | None:
        return self._workspaces.get(workspace_id)

    def all(self) -> list[Workspace]:
        return list(self._workspaces.values())

    @property
    def active(self) -> Workspace | None:
        return self._workspaces.get(self._active_id) if self._active_id else None

    def set_active(self, workspace_id: str) -> None:
        if workspace_id not in self._workspaces:
            raise KeyError(f"Unknown workspace '{workspace_id}'")
        self._active_id = workspace_id
        logger.debug("Active workspace set to '%s'", workspace_id)
