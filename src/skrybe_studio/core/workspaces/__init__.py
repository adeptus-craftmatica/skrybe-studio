"""Workspace and panel registration - screens as views over shared plugin-registered panels."""

from skrybe_studio.core.workspaces.models import PanelPlacement, Workspace
from skrybe_studio.core.workspaces.panels import (
    DuplicatePanelError,
    PanelRegistry,
    find_enclosing_main_window,
)
from skrybe_studio.core.workspaces.registry import DuplicateWorkspaceError, WorkspaceRegistry

__all__ = [
    "DuplicatePanelError",
    "DuplicateWorkspaceError",
    "PanelPlacement",
    "PanelRegistry",
    "Workspace",
    "WorkspaceRegistry",
    "find_enclosing_main_window",
]
