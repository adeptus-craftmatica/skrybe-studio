"""Resolves OS-appropriate application directories. Never hardcode a path outside this module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import platformdirs

APP_NAME = "Skrybe Studio"
APP_AUTHOR = "adeptus-craftmatica"


@dataclass(frozen=True, slots=True)
class ApplicationPaths:
    config_dir: Path
    data_dir: Path
    log_dir: Path
    cache_dir: Path

    @property
    def app_settings_file(self) -> Path:
        return self.config_dir / "settings.json"

    @property
    def builtin_plugins_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent / "plugins"


def resolve_application_paths() -> ApplicationPaths:
    return ApplicationPaths(
        config_dir=Path(platformdirs.user_config_dir(APP_NAME, APP_AUTHOR)),
        data_dir=Path(platformdirs.user_data_dir(APP_NAME, APP_AUTHOR)),
        log_dir=Path(platformdirs.user_log_dir(APP_NAME, APP_AUTHOR)),
        cache_dir=Path(platformdirs.user_cache_dir(APP_NAME, APP_AUTHOR)),
    )
