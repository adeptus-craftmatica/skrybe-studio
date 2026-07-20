"""Exercises plugin discovery: validation, duplicate/circular/missing dependency
detection, load ordering, and entrypoint-failure isolation.

Fixture plugins are written to `tmp_path` as real importable `.py` files
(unique module names per test, via `monkeypatch.syspath_prepend`) so the
loader's real `importlib.import_module` codepath is exercised, not a mock.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from skrybe_studio.core.plugins.loader import PluginLoader

GOOD_PLUGIN_SOURCE = """
from skrybe_studio.core.plugins.base import Plugin


class {class_name}(Plugin):
    def register(self, context):
        pass
"""

BROKEN_IMPORT_SOURCE = """
raise ImportError("simulated broken import")
"""

NOT_A_PLUGIN_SOURCE = """
class {class_name}:
    pass
"""


def _write_plugin(
    plugins_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    plugin_id: str,
    dir_name: str | None = None,
    requires: list[str] | None = None,
    optional_requires: list[str] | None = None,
    source_template: str | None = GOOD_PLUGIN_SOURCE,
    manifest_overrides: dict | None = None,
    manifest_text: str | None = None,
) -> Path:
    slug = plugin_id.rsplit(".", 1)[-1]
    module_name = f"_loader_fixture_{slug}_{uuid4().hex}"
    class_name = "FixturePlugin"

    module_dir = plugins_dir.parent / "_modules"
    module_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.syspath_prepend(str(module_dir))

    if source_template is not None:
        (module_dir / f"{module_name}.py").write_text(
            source_template.format(class_name=class_name), encoding="utf-8"
        )

    plugin_dir = plugins_dir / (dir_name or slug)
    plugin_dir.mkdir(parents=True, exist_ok=True)

    if manifest_text is not None:
        (plugin_dir / "manifest.json").write_text(manifest_text, encoding="utf-8")
        return plugin_dir

    manifest = {
        "id": plugin_id,
        "name": slug.title(),
        "version": "0.1.0",
        "api_version": "1",
        "entrypoint": f"{module_name}:{class_name}",
        "requires": requires or [],
        "optional_requires": optional_requires or [],
    }
    if manifest_overrides:
        manifest.update(manifest_overrides)
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return plugin_dir


def test_discovers_and_instantiates_valid_plugin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugins_dir = tmp_path / "plugins"
    _write_plugin(plugins_dir, monkeypatch, plugin_id="com.example.a")

    result = PluginLoader([plugins_dir]).discover_and_instantiate()

    assert [loaded.manifest.id for loaded in result.loaded] == ["com.example.a"]
    assert result.failures == []


def test_duplicate_plugin_id_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plugins_dir = tmp_path / "plugins"
    _write_plugin(plugins_dir, monkeypatch, plugin_id="com.example.dup", dir_name="first")
    _write_plugin(plugins_dir, monkeypatch, plugin_id="com.example.dup", dir_name="second")

    result = PluginLoader([plugins_dir]).discover_and_instantiate()

    assert len(result.loaded) == 1
    assert any(f.category == "duplicate_plugin_id" for f in result.failures)


def test_invalid_manifest_json_is_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugins_dir = tmp_path / "plugins"
    _write_plugin(
        plugins_dir, monkeypatch, plugin_id="com.example.bad", manifest_text="{not valid json"
    )

    result = PluginLoader([plugins_dir]).discover_and_instantiate()

    assert result.loaded == []
    assert result.failures[0].category == "invalid_manifest"


def test_unsupported_api_version_is_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugins_dir = tmp_path / "plugins"
    _write_plugin(
        plugins_dir,
        monkeypatch,
        plugin_id="com.example.future",
        manifest_overrides={"api_version": "99"},
    )

    result = PluginLoader([plugins_dir]).discover_and_instantiate()

    assert result.loaded == []
    assert result.failures[0].category == "unsupported_api_version"


def test_missing_dependency_is_a_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plugins_dir = tmp_path / "plugins"
    _write_plugin(
        plugins_dir, monkeypatch, plugin_id="com.example.needs", requires=["com.example.absent"]
    )

    result = PluginLoader([plugins_dir]).discover_and_instantiate()

    assert result.loaded == []
    assert any(f.category == "missing_dependency" for f in result.failures)


def test_circular_dependency_is_a_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plugins_dir = tmp_path / "plugins"
    _write_plugin(plugins_dir, monkeypatch, plugin_id="com.example.a", requires=["com.example.b"])
    _write_plugin(plugins_dir, monkeypatch, plugin_id="com.example.b", requires=["com.example.a"])

    result = PluginLoader([plugins_dir]).discover_and_instantiate()

    assert result.loaded == []
    assert any(f.category == "circular_dependency" for f in result.failures)


def test_dependencies_load_before_dependents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugins_dir = tmp_path / "plugins"
    _write_plugin(plugins_dir, monkeypatch, plugin_id="com.example.base")
    _write_plugin(
        plugins_dir, monkeypatch, plugin_id="com.example.dependent", requires=["com.example.base"]
    )

    result = PluginLoader([plugins_dir]).discover_and_instantiate()

    order = [loaded.manifest.id for loaded in result.loaded]
    assert order.index("com.example.base") < order.index("com.example.dependent")


def test_broken_entrypoint_does_not_prevent_other_plugins_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugins_dir = tmp_path / "plugins"
    _write_plugin(
        plugins_dir,
        monkeypatch,
        plugin_id="com.example.broken",
        source_template=BROKEN_IMPORT_SOURCE,
    )
    _write_plugin(plugins_dir, monkeypatch, plugin_id="com.example.healthy")

    result = PluginLoader([plugins_dir]).discover_and_instantiate()

    assert [loaded.manifest.id for loaded in result.loaded] == ["com.example.healthy"]
    assert any(f.category == "entrypoint_error" for f in result.failures)


def test_entrypoint_not_implementing_plugin_is_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugins_dir = tmp_path / "plugins"
    _write_plugin(
        plugins_dir,
        monkeypatch,
        plugin_id="com.example.notaplugin",
        source_template=NOT_A_PLUGIN_SOURCE,
    )

    result = PluginLoader([plugins_dir]).discover_and_instantiate()

    assert result.loaded == []
    assert result.failures[0].category == "entrypoint_error"
