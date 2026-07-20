"""Layout of a `.skrybe` project directory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_SUFFIX = ".skrybe"


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    """Resolves every well-known path inside a project's root directory."""

    root: Path

    @property
    def metadata_file(self) -> Path:
        return self.root / "project.json"

    @property
    def database_file(self) -> Path:
        return self.root / "project.db"

    @property
    def documents_dir(self) -> Path:
        return self.root / "documents"

    @property
    def assets_dir(self) -> Path:
        return self.root / "assets"

    @property
    def exports_dir(self) -> Path:
        return self.root / "exports"

    @property
    def cache_dir(self) -> Path:
        return self.root / "cache"

    @property
    def backups_dir(self) -> Path:
        return self.root / "backups"

    @property
    def settings_file(self) -> Path:
        return self.cache_dir / "project-settings.json"

    def all_directories(self) -> tuple[Path, ...]:
        return (
            self.documents_dir,
            self.assets_dir,
            self.exports_dir,
            self.cache_dir,
            self.backups_dir,
        )
