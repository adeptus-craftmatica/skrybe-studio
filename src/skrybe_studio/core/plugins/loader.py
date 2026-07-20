"""Discovers, validates, orders, and instantiates plugins.

A broken plugin - an invalid manifest, an unsupported API version, a
missing or circular dependency, or an entrypoint that fails to import -
is recorded as a `PluginLoadFailure` and skipped. It never raises out of
`discover_and_instantiate`, so one broken optional plugin can never
prevent the rest of the application (or other plugins) from starting.
"""

from __future__ import annotations

import importlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from skrybe_studio.core.plugins.base import Plugin
from skrybe_studio.core.plugins.errors import EntrypointLoadError
from skrybe_studio.core.plugins.manifest import PluginManifest

logger = logging.getLogger(__name__)

ManifestLocation = tuple[PluginManifest, Path]


@dataclass(slots=True)
class LoadedPlugin:
    manifest: PluginManifest
    instance: Plugin
    directory: Path


@dataclass(slots=True)
class PluginLoadFailure:
    plugin_id: str
    directory: Path
    category: str
    reason: str


@dataclass(slots=True)
class PluginDiscoveryResult:
    loaded: list[LoadedPlugin] = field(default_factory=list)
    failures: list[PluginLoadFailure] = field(default_factory=list)


class PluginLoader:
    """Discovers manifests under one or more plugin directories and loads them."""

    def __init__(self, plugin_directories: list[Path]) -> None:
        self._plugin_directories = plugin_directories

    def discover_manifests(
        self,
    ) -> tuple[dict[str, ManifestLocation], list[PluginLoadFailure]]:
        manifests: dict[str, ManifestLocation] = {}
        failures: list[PluginLoadFailure] = []
        for directory in self._plugin_directories:
            if not directory.is_dir():
                continue
            for plugin_dir in sorted(p for p in directory.iterdir() if p.is_dir()):
                manifest_path = plugin_dir / "manifest.json"
                if not manifest_path.exists():
                    continue
                manifest = self._load_manifest(plugin_dir, manifest_path, failures)
                if manifest is None:
                    continue
                if not manifest.is_api_version_supported():
                    failures.append(
                        PluginLoadFailure(
                            plugin_id=manifest.id,
                            directory=plugin_dir,
                            category="unsupported_api_version",
                            reason=f"Unsupported api_version '{manifest.api_version}'",
                        )
                    )
                    continue
                if manifest.id in manifests:
                    failures.append(
                        PluginLoadFailure(
                            plugin_id=manifest.id,
                            directory=plugin_dir,
                            category="duplicate_plugin_id",
                            reason=f"Duplicate plugin id '{manifest.id}'",
                        )
                    )
                    continue
                manifests[manifest.id] = (manifest, plugin_dir)
        return manifests, failures

    @staticmethod
    def _load_manifest(
        plugin_dir: Path, manifest_path: Path, failures: list[PluginLoadFailure]
    ) -> PluginManifest | None:
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            return PluginManifest.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            failures.append(
                PluginLoadFailure(
                    plugin_id=plugin_dir.name,
                    directory=plugin_dir,
                    category="invalid_manifest",
                    reason=f"Invalid manifest: {exc}",
                )
            )
            return None

    def resolve_load_order(
        self, manifests: dict[str, ManifestLocation]
    ) -> tuple[list[str], list[PluginLoadFailure]]:
        """Topologically sort by `requires`, detecting missing and circular dependencies."""
        failures: list[PluginLoadFailure] = []
        order: list[str] = []
        state: dict[str, str] = {}  # plugin_id -> "visiting" | "done" | "failed"

        def visit(plugin_id: str, chain: tuple[str, ...]) -> bool:
            current_state = state.get(plugin_id)
            if current_state == "done":
                return True
            if current_state == "failed":
                return False
            if current_state == "visiting":
                cycle = " -> ".join((*chain, plugin_id))
                failures.append(
                    PluginLoadFailure(
                        plugin_id=plugin_id,
                        directory=manifests[plugin_id][1],
                        category="circular_dependency",
                        reason=f"Circular dependency detected: {cycle}",
                    )
                )
                state[plugin_id] = "failed"
                return False

            state[plugin_id] = "visiting"
            manifest, directory = manifests[plugin_id]
            for dependency_id in manifest.requires:
                if dependency_id not in manifests:
                    failures.append(
                        PluginLoadFailure(
                            plugin_id=plugin_id,
                            directory=directory,
                            category="missing_dependency",
                            reason=f"Missing required dependency '{dependency_id}'",
                        )
                    )
                    state[plugin_id] = "failed"
                    return False
                if not visit(dependency_id, (*chain, plugin_id)):
                    state[plugin_id] = "failed"
                    return False
            for dependency_id in manifest.optional_requires:
                if dependency_id in manifests:
                    visit(dependency_id, (*chain, plugin_id))

            state[plugin_id] = "done"
            order.append(plugin_id)
            return True

        for plugin_id in manifests:
            if state.get(plugin_id) is None:
                visit(plugin_id, ())

        return order, failures

    @staticmethod
    def instantiate(manifest: PluginManifest) -> Plugin:
        module_path, _, class_name = manifest.entrypoint.partition(":")
        try:
            module = importlib.import_module(module_path)
            plugin_class = getattr(module, class_name)
            instance = plugin_class()
        except Exception as exc:
            raise EntrypointLoadError(
                f"Failed to load entrypoint '{manifest.entrypoint}' "
                f"for plugin '{manifest.id}': {exc}"
            ) from exc
        if not isinstance(instance, Plugin):
            raise EntrypointLoadError(
                f"Entrypoint '{manifest.entrypoint}' for plugin '{manifest.id}' "
                "does not implement the Plugin interface"
            )
        return instance

    def discover_and_instantiate(self) -> PluginDiscoveryResult:
        manifests, failures = self.discover_manifests()
        order, order_failures = self.resolve_load_order(manifests)
        failures.extend(order_failures)
        result = PluginDiscoveryResult(failures=failures)

        for plugin_id in order:
            manifest, directory = manifests[plugin_id]
            try:
                instance = self.instantiate(manifest)
            except EntrypointLoadError as exc:
                logger.error("Failed to load plugin '%s': %s", plugin_id, exc)
                result.failures.append(
                    PluginLoadFailure(
                        plugin_id=plugin_id,
                        directory=directory,
                        category="entrypoint_error",
                        reason=str(exc),
                    )
                )
                continue
            result.loaded.append(
                LoadedPlugin(manifest=manifest, instance=instance, directory=directory)
            )
            logger.info("Loaded plugin '%s' v%s", plugin_id, manifest.version)

        for failure in result.failures:
            logger.warning(
                "Plugin '%s' not loaded (%s): %s",
                failure.plugin_id,
                failure.category,
                failure.reason,
            )
        return result
