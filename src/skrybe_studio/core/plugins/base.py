"""The stable plugin lifecycle contract every plugin implements."""

from __future__ import annotations

from abc import ABC, abstractmethod

from skrybe_studio.core.plugins.context import PluginContext, ProjectContext


class Plugin(ABC):
    """Lifecycle: `register` (once) -> `activate`/`deactivate` (per project) -> `shutdown` (once)."""

    @abstractmethod
    def register(self, context: PluginContext) -> None:
        """Register commands, panels, workspaces, and event handlers. Called once at startup."""

    def activate(self, context: ProjectContext) -> None:  # noqa: B027
        """Called when a project opens, with that project's scoped services. Optional."""

    def deactivate(self, context: ProjectContext) -> None:  # noqa: B027
        """Called when the active project closes. Optional."""

    def shutdown(self, context: PluginContext) -> None:  # noqa: B027
        """Called once at application shutdown to release resources. Optional."""
