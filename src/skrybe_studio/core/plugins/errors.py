"""Exception types raised while loading plugins.

The loader itself never lets these propagate out of plugin discovery -
see `PluginLoader.discover_and_instantiate`, which converts every one of
these into a collected `PluginLoadFailure` so a broken plugin can never
take down the whole application. They remain useful for direct,
lower-level use (e.g. in tests, or the standalone plugin host).
"""

from __future__ import annotations


class PluginError(RuntimeError):
    """Base class for all plugin-loading errors."""


class ManifestValidationError(PluginError):
    """Raised when a plugin manifest fails schema validation."""


class DuplicatePluginError(PluginError):
    """Raised when two discovered manifests declare the same plugin ID."""


class UnsupportedApiVersionError(PluginError):
    """Raised when a manifest declares an `api_version` the host does not support."""


class MissingDependencyError(PluginError):
    """Raised when a plugin's `requires` names a plugin that was not discovered."""


class CircularDependencyError(PluginError):
    """Raised when plugin `requires` form a dependency cycle."""


class EntrypointLoadError(PluginError):
    """Raised when a manifest's entrypoint cannot be imported or instantiated."""
