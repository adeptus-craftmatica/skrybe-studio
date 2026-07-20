from __future__ import annotations

from pathlib import Path

from skrybe_studio.core.entities.relationships import RelationshipService
from skrybe_studio.core.entities.service import EntityService
from skrybe_studio.core.storage.database import Database


def _database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "project.db")
    database.create_core_tables()
    return database


def test_create_and_get_entity(tmp_path: Path) -> None:
    service = EntityService(_database(tmp_path))

    entity = service.create(entity_type="notes.note", title="My Note", plugin_owner="notes")

    fetched = service.get(entity.id)
    assert fetched is not None
    assert fetched.title == "My Note"
    assert fetched.entity_type == "notes.note"
    assert not fetched.is_deleted


def test_soft_delete_hides_entity_by_default(tmp_path: Path) -> None:
    service = EntityService(_database(tmp_path))
    entity = service.create(entity_type="notes.note", title="Gone", plugin_owner="notes")

    assert service.soft_delete(entity.id) is True

    assert service.get(entity.id) is None
    assert service.get(entity.id, include_deleted=True) is not None


def test_list_filters_by_type_and_owner(tmp_path: Path) -> None:
    service = EntityService(_database(tmp_path))
    service.create(entity_type="notes.note", title="A", plugin_owner="notes")
    service.create(entity_type="assets.asset", title="B", plugin_owner="assets")

    notes = service.list(entity_type="notes.note")

    assert [e.title for e in notes] == ["A"]


def test_update_changes_title_and_metadata(tmp_path: Path) -> None:
    service = EntityService(_database(tmp_path))
    entity = service.create(entity_type="notes.note", title="Old", plugin_owner="notes")

    updated = service.update(entity.id, title="New", metadata={"pinned": True})

    assert updated is not None
    assert updated.title == "New"
    assert updated.metadata == {"pinned": True}
    assert updated.updated_at >= entity.updated_at


def test_relationship_links_two_entities(tmp_path: Path) -> None:
    database = _database(tmp_path)
    entities = EntityService(database)
    relationships = RelationshipService(database)

    a = entities.create(entity_type="notes.note", title="A", plugin_owner="notes")
    b = entities.create(entity_type="notes.note", title="B", plugin_owner="notes")

    relationship = relationships.create(
        source_entity_id=a.id,
        target_entity_id=b.id,
        relationship_type="references",
        plugin_owner="notes",
    )

    linked = relationships.for_entity(a.id)
    assert len(linked) == 1
    assert linked[0].id == relationship.id

    assert relationships.delete(relationship.id) is True
    assert relationships.for_entity(a.id) == []
