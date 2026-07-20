"""Project lifecycle errors."""

from __future__ import annotations


class ProjectError(RuntimeError):
    """Base class for project lifecycle errors."""


class ProjectAlreadyExistsError(ProjectError):
    """Raised when creating a project would overwrite an existing, non-empty directory."""


class ProjectNotFoundError(ProjectError):
    """Raised when opening a project whose directory does not exist."""


class InvalidProjectError(ProjectError):
    """Raised when a project directory is missing or has an invalid `project.json`."""
