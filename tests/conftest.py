"""Shared fixtures. Every test runs against isolated temporary directories -
never the real user home, app-support, or log directories.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from skrybe_studio.app.bootstrap import Application
from skrybe_studio.app.paths import ApplicationPaths


@pytest.fixture(autouse=True)
def _qapp(qapp):
    """Guarantees a QApplication exists for every test (pytest-qt supplies `qapp`)."""
    return qapp


@pytest.fixture
def app_paths(tmp_path: Path) -> ApplicationPaths:
    base = tmp_path / "app-support"
    return ApplicationPaths(
        config_dir=base / "config",
        data_dir=base / "data",
        log_dir=base / "logs",
        cache_dir=base / "cache",
    )


@pytest.fixture
def application(app_paths: ApplicationPaths) -> Iterator[Application]:
    app = Application(paths=app_paths)
    yield app
    app.shutdown()


@pytest.fixture
def loaded_application(application: Application) -> Application:
    application.load_plugins()
    return application


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    return tmp_path / "TestProject"
