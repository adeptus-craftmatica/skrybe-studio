"""Workspace and panel registration - screens as views over shared plugin-registered panels."""

from skrybe_studio.core.workspaces.models import PanelPlacement, Workspace
from skrybe_studio.core.workspaces.panels import DuplicatePanelError, PanelRegistry
from skrybe_studio.core.workspaces.registry import DuplicateWorkspaceError, WorkspaceRegistry

__all__ = [
    "DuplicatePanelError",
    "DuplicateWorkspaceError",
    "PanelPlacement",
    "PanelRegistry",
    "Workspace",
    "WorkspaceRegistry",
]
