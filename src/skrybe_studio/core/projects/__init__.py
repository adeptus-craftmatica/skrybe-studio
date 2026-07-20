"""The `.skrybe` project lifecycle: create, open, close, validate."""

from skrybe_studio.core.projects.errors import (
    InvalidProjectError,
    ProjectAlreadyExistsError,
    ProjectError,
    ProjectNotFoundError,
)
from skrybe_studio.core.projects.models import ProjectMetadata
from skrybe_studio.core.projects.paths import PROJECT_SUFFIX, ProjectPaths
from skrybe_studio.core.projects.recent import RecentProjectsStore
from skrybe_studio.core.projects.service import OpenProject, ProjectService

__all__ = [
    "PROJECT_SUFFIX",
    "InvalidProjectError",
    "OpenProject",
    "ProjectAlreadyExistsError",
    "ProjectError",
    "ProjectMetadata",
    "ProjectNotFoundError",
    "ProjectPaths",
    "ProjectService",
    "RecentProjectsStore",
]
