from __future__ import annotations

from pathlib import Path

import pytest

from skrybe_studio.core.projects.errors import InvalidProjectError, ProjectNotFoundError
from skrybe_studio.core.projects.service import ProjectService
from skrybe_studio.core.settings.service import SettingsService


def _service(tmp_path: Path) -> ProjectService:
    return ProjectService(SettingsService(tmp_path / "app-settings.json"))


def test_create_project_creates_expected_layout(project_root: Path, tmp_path: Path) -> None:
    service = _service(tmp_path)

    project = service.create(project_root, "My Novel")

    assert project.paths.root.name.endswith(".skrybe")
    assert project.paths.metadata_file.exists()
    assert project.paths.documents_dir.is_dir()
    assert project.paths.assets_dir.is_dir()
    assert project.paths.exports_dir.is_dir()
    assert project.paths.cache_dir.is_dir()
    assert project.paths.backups_dir.is_dir()
    assert project.metadata.name == "My Novel"


def test_create_adds_skrybe_suffix_when_missing(project_root: Path, tmp_path: Path) -> None:
    service = _service(tmp_path)
    project = service.create(project_root, "My Novel")
    assert project.paths.root == project_root.with_name(project_root.name + ".skrybe")


def test_open_reads_back_metadata(project_root: Path, tmp_path: Path) -> None:
    service = _service(tmp_path)
    created = service.create(project_root, "My Novel")
    service.close()

    reopened = _service(tmp_path).open(created.paths.root)

    assert reopened.metadata.name == "My Novel"
    assert reopened.metadata.id == created.metadata.id


def test_open_missing_directory_raises(tmp_path: Path) -> None:
    service = _service(tmp_path)
    with pytest.raises(ProjectNotFoundError):
        service.open(tmp_path / "does-not-exist.skrybe")


def test_open_directory_missing_project_json_raises(tmp_path: Path) -> None:
    root = tmp_path / "Empty.skrybe"
    root.mkdir()
    service = _service(tmp_path)
    with pytest.raises(InvalidProjectError):
        service.open(root)


def test_close_then_current_is_none(project_root: Path, tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create(project_root, "My Novel")

    service.close()

    assert service.current is None


def test_record_opened_appears_in_recent_projects(project_root: Path, tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create(project_root, "My Novel")

    recent = service.recent_projects.all()

    assert service.current is not None
    assert recent[0]["name"] == "My Novel"
    assert recent[0]["path"] == str(service.current.paths.root)
