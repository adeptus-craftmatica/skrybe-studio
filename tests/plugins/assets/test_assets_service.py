from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QImage

from skrybe_studio.core.entities.service import EntityService
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.core.jobs.manager import JobManager
from skrybe_studio.core.storage.database import Database
from skrybe_studio.plugins.assets.application.events import AssetImported, AssetRemoved
from skrybe_studio.plugins.assets.application.service import AssetsService
from skrybe_studio.plugins.assets.domain.asset import ENTITY_TYPE
from skrybe_studio.plugins.assets.infrastructure.models import AssetsBase
from skrybe_studio.plugins.assets.infrastructure.repository import AssetRepository


def _service(tmp_path: Path) -> tuple[AssetsService, EntityService, EventBus, JobManager]:
    database = Database(tmp_path / "project.db")
    database.create_core_tables()
    AssetsBase.metadata.create_all(database.engine)
    entities = EntityService(database)
    events = EventBus()
    jobs = JobManager()
    repository = AssetRepository(database)
    assets_dir = tmp_path / "assets"
    cache_dir = tmp_path / "cache" / "thumbnails"
    service = AssetsService(repository, entities, events, jobs, assets_dir, cache_dir)
    return service, entities, events, jobs


def _make_image(path: Path, color: str = "red") -> Path:
    image = QImage(16, 16, QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    image.save(str(path))
    return path


def test_import_asset_creates_entity_and_publishes_event(tmp_path: Path, qapp) -> None:
    service, entities, events, jobs = _service(tmp_path)
    received: list[str] = []
    events.subscribe(AssetImported, lambda event: received.append(event.original_filename))
    source = _make_image(tmp_path / "source.png")

    asset_id = service.import_asset(source)
    jobs.wait_for_done(5000)
    qapp.processEvents()

    asset = service.get_asset(asset_id)
    assert asset is not None
    assert asset.original_filename == "source.png"
    assert asset.content_hash

    entity = entities.get(asset_id)
    assert entity is not None
    assert entity.entity_type == ENTITY_TYPE
    assert received == ["source.png"]


def test_import_copies_file_into_managed_assets_directory(tmp_path: Path, qapp) -> None:
    service, _entities, _events, jobs = _service(tmp_path)
    source = _make_image(tmp_path / "source.png")

    asset_id = service.import_asset(source)
    jobs.wait_for_done(5000)
    qapp.processEvents()

    asset = service.get_asset(asset_id)
    assert asset is not None
    stored_path = service.resolve_path(asset)
    assert stored_path.exists()
    assert stored_path.parent == tmp_path / "assets"
    assert stored_path != source


def test_thumbnail_is_generated_for_images(tmp_path: Path, qapp) -> None:
    service, _entities, _events, jobs = _service(tmp_path)
    source = _make_image(tmp_path / "source.png")

    asset_id = service.import_asset(source)
    jobs.wait_for_done(5000)
    qapp.processEvents()

    assert service.thumbnail_path(asset_id) is not None


def test_duplicate_content_is_detected_and_not_duplicated(tmp_path: Path, qapp) -> None:
    service, _entities, _events, jobs = _service(tmp_path)
    source_a = _make_image(tmp_path / "a.png", "blue")
    source_b = _make_image(tmp_path / "b.png", "blue")  # identical pixel content -> identical hash

    service.import_asset(source_a)
    jobs.wait_for_done(5000)
    qapp.processEvents()
    service.import_asset(source_b)
    jobs.wait_for_done(5000)
    qapp.processEvents()

    assert len(service.list_assets()) == 1


def test_missing_file_is_detected(tmp_path: Path, qapp) -> None:
    service, _entities, _events, jobs = _service(tmp_path)
    source = _make_image(tmp_path / "source.png")

    asset_id = service.import_asset(source)
    jobs.wait_for_done(5000)
    qapp.processEvents()

    asset = service.get_asset(asset_id)
    assert asset is not None
    assert service.is_missing(asset) is False

    service.resolve_path(asset).unlink()

    reloaded_asset = service.get_asset(asset_id)
    assert reloaded_asset is not None
    assert service.is_missing(reloaded_asset) is True


def test_remove_asset_deletes_file_entity_and_publishes_event(tmp_path: Path, qapp) -> None:
    service, entities, events, jobs = _service(tmp_path)
    received: list[object] = []
    events.subscribe(AssetRemoved, received.append)
    source = _make_image(tmp_path / "source.png")

    asset_id = service.import_asset(source)
    jobs.wait_for_done(5000)
    qapp.processEvents()
    asset_before_removal = service.get_asset(asset_id)
    assert asset_before_removal is not None
    stored_path = service.resolve_path(asset_before_removal)

    assert service.remove_asset(asset_id) is True

    assert service.get_asset(asset_id) is None
    assert entities.get(asset_id) is None
    assert not stored_path.exists()
    assert len(received) == 1


def test_search_matches_tags(tmp_path: Path, qapp) -> None:
    service, _entities, _events, jobs = _service(tmp_path)
    source = _make_image(tmp_path / "cover-art.png")

    asset_id = service.import_asset(source)
    jobs.wait_for_done(5000)
    qapp.processEvents()
    service.set_tags(asset_id, ("worldbuilding", "map"))

    results = service.search_assets("worldbuilding")

    assert [asset.id for asset in results] == [asset_id]
