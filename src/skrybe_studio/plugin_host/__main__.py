"""Standalone plugin host entry point.

    uv run python -m skrybe_studio.plugin_host --plugin notes

Loads every plugin (so `requires` dependencies still resolve), but only
opens a window for the requested one, backed by a persistent per-plugin
development project under the application data directory.
"""

from __future__ import annotations

import argparse
import sys

from PySide6.QtWidgets import QApplication

from skrybe_studio.app.bootstrap import Application
from skrybe_studio.app.paths import resolve_application_paths
from skrybe_studio.core.plugins.loader import LoadedPlugin
from skrybe_studio.plugin_host.window import PluginHostWindow


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="skrybe-plugin-host", description="Run a single Skrybe Studio plugin standalone."
    )
    parser.add_argument(
        "--plugin", required=True, help="Plugin id, or a substring of it (e.g. 'notes')."
    )
    return parser.parse_args(argv)


def _find_plugin(application: Application, needle: str) -> LoadedPlugin | None:
    needle = needle.lower()
    for loaded in application.loaded_plugins:
        if needle == loaded.manifest.id.lower() or needle in loaded.manifest.id.lower():
            return loaded
    return None


def _print_available(application: Application) -> None:
    print("Available plugins:", file=sys.stderr)
    for loaded in application.loaded_plugins:
        print(f"  - {loaded.manifest.id}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    qt_app = QApplication(sys.argv[:1])
    qt_app.setApplicationName("Skrybe Studio Plugin Host")
    qt_app.setOrganizationName("adeptus-craftmatica")

    application = Application()
    application.load_plugins()

    target = _find_plugin(application, args.plugin)
    if target is None:
        print(f"No loaded plugin matches '{args.plugin}'.", file=sys.stderr)
        _print_available(application)
        return 1

    dev_project_root = (
        resolve_application_paths().data_dir / "plugin-host" / f"{target.manifest.id}.skrybe"
    )
    dev_project_root.parent.mkdir(parents=True, exist_ok=True)
    if dev_project_root.exists():
        application.open_project(dev_project_root)
    else:
        application.create_project(dev_project_root, f"{target.manifest.name} (Plugin Host)")

    window = PluginHostWindow(application, target)
    window.show()

    exit_code = qt_app.exec()
    application.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
