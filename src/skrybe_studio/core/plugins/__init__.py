"""The plugin contract, manifest schema, and discovery/loading machinery."""

from skrybe_studio.core.plugins.base import Plugin
from skrybe_studio.core.plugins.context import PluginContext, ProjectContext
from skrybe_studio.core.plugins.errors import (
    EntrypointLoadError,
    PluginError,
)
from skrybe_studio.core.plugins.loader import (
    LoadedPlugin,
    PluginDiscoveryResult,
    PluginLoader,
    PluginLoadFailure,
)
from skrybe_studio.core.plugins.manifest import PluginManifest

__all__ = [
    "EntrypointLoadError",
    "LoadedPlugin",
    "Plugin",
    "PluginContext",
    "PluginDiscoveryResult",
    "PluginError",
    "PluginLoadFailure",
    "PluginLoader",
    "PluginManifest",
    "ProjectContext",
]
