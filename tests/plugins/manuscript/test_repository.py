from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from skrybe_studio.core.storage.database import Database
from skrybe_studio.plugins.manuscript.domain.document_ir import paragraph
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType
from skrybe_studio.plugins.manuscript.domain.models import ManuscriptNode, Snapshot
from skrybe_studio.plugins.manuscript.infrastructure.models import ManuscriptBase
from skrybe_studio.plugins.manuscript.infrastructure.repositories import (
    ManuscriptRepository,
    ProgressRepository,
    SnapshotRepository,
    sort_order_between,
)


@pytest.fixture
def database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "project.db")
    database.create_core_tables()
    ManuscriptBase.metadata.create_all(database.engine)
    return database


@pytest.fixture
def repository(database: Database) -> ManuscriptRepository:
    return ManuscriptRepository(database)


def _node(
    *,
    node_id=None,
    manuscript_id=None,
    parent_id=None,
    node_type=ManuscriptNodeType.MANUSCRIPT,
    title="Untitled",
    sort_order=0.0,
) -> ManuscriptNode:
    now = datetime.now(UTC)
    node_id = node_id or uuid4()
    return ManuscriptNode(
        id=node_id,
        manuscript_id=manuscript_id or node_id,
        parent_id=parent_id,
        node_type=node_type,
        title=title,
        sort_order=sort_order,
        created_at=now,
        updated_at=now,
    )


def test_sort_order_between_produces_a_deterministic_midpoint() -> None:
    assert sort_order_between(None, None) > 0
    assert sort_order_between(1.0, 3.0) == 2.0
    assert sort_order_between(None, 5.0) < 5.0
    assert sort_order_between(5.0, None) > 5.0


def test_add_and_get_node(repository: ManuscriptRepository) -> None:
    root = _node(title="My Novel")
    repository.add_node(root)

    fetched = repository.get_node(root.id)

    assert fetched is not None
    assert fetched.title == "My Novel"
    assert fetched.node_type == ManuscriptNodeType.MANUSCRIPT


def test_list_children_orders_by_sort_order(repository: ManuscriptRepository) -> None:
    root = _node(title="Root")
    repository.add_node(root)
    second = _node(
        manuscript_id=root.id,
        parent_id=root.id,
        node_type=ManuscriptNodeType.CHAPTER,
        title="B",
        sort_order=2.0,
    )
    first = _node(
        manuscript_id=root.id,
        parent_id=root.id,
        node_type=ManuscriptNodeType.CHAPTER,
        title="A",
        sort_order=1.0,
    )
    repository.add_node(second)
    repository.add_node(first)

    children = repository.list_children(root.id)

    assert [child.title for child in children] == ["A", "B"]


def test_reordering_only_touches_the_moved_row(repository: ManuscriptRepository) -> None:
    root = _node()
    repository.add_node(root)
    a = _node(
        manuscript_id=root.id,
        parent_id=root.id,
        node_type=ManuscriptNodeType.CHAPTER,
        title="A",
        sort_order=1.0,
    )
    b = _node(
        manuscript_id=root.id,
        parent_id=root.id,
        node_type=ManuscriptNodeType.CHAPTER,
        title="B",
        sort_order=2.0,
    )
    repository.add_node(a)
    repository.add_node(b)

    new_order = sort_order_between(a.sort_order, b.sort_order)
    repository.set_sort_order(b.id, new_order)
    repository.set_sort_order(a.id, sort_order_between(None, new_order))

    # `a`'s row identity/content besides sort_order is untouched.
    reloaded_a = repository.get_node(a.id)
    assert reloaded_a is not None
    assert reloaded_a.title == "A"


def test_subtree_lists_node_and_all_descendants(repository: ManuscriptRepository) -> None:
    root = _node()
    repository.add_node(root)
    chapter = _node(
        manuscript_id=root.id, parent_id=root.id, node_type=ManuscriptNodeType.CHAPTER, title="Ch1"
    )
    repository.add_node(chapter)
    scene = _node(
        manuscript_id=root.id, parent_id=chapter.id, node_type=ManuscriptNodeType.SCENE, title="Sc1"
    )
    repository.add_node(scene)

    subtree = repository.list_subtree(root.id)

    assert {node.title for node in subtree} == {root.title, "Ch1", "Sc1"}


def test_archive_cascades_to_descendants(repository: ManuscriptRepository) -> None:
    root = _node()
    repository.add_node(root)
    chapter = _node(
        manuscript_id=root.id, parent_id=root.id, node_type=ManuscriptNodeType.CHAPTER, title="Ch1"
    )
    repository.add_node(chapter)
    scene = _node(
        manuscript_id=root.id, parent_id=chapter.id, node_type=ManuscriptNodeType.SCENE, title="Sc1"
    )
    repository.add_node(scene)

    repository.set_archived([chapter.id, scene.id], datetime.now(UTC))

    assert repository.list_children(root.id) == []  # chapter is archived, excluded by default
    archived_chapter = repository.get_node(chapter.id)
    archived_scene = repository.get_node(scene.id)
    assert archived_chapter is not None
    assert archived_scene is not None
    assert archived_chapter.is_archived is True
    assert archived_scene.is_archived is True


def test_restore_clears_archived_at(repository: ManuscriptRepository) -> None:
    root = _node()
    repository.add_node(root)
    chapter = _node(
        manuscript_id=root.id, parent_id=root.id, node_type=ManuscriptNodeType.CHAPTER, title="Ch1"
    )
    repository.add_node(chapter)
    repository.set_archived([chapter.id], datetime.now(UTC))

    repository.set_archived([chapter.id], None)

    restored_chapter = repository.get_node(chapter.id)
    assert restored_chapter is not None
    assert restored_chapter.is_archived is False
    assert [n.title for n in repository.list_children(root.id)] == ["Ch1"]


def test_document_content_persists_and_updates_word_count(repository: ManuscriptRepository) -> None:
    root = _node()
    repository.add_node(root)
    scene = _node(
        manuscript_id=root.id, parent_id=root.id, node_type=ManuscriptNodeType.SCENE, title="Sc1"
    )
    repository.add_node(scene)

    word_count = repository.save_document_content(scene.id, (paragraph("one two three"),))

    assert word_count == 3
    scene_after_save = repository.get_node(scene.id)
    assert scene_after_save is not None
    assert scene_after_save.word_count == 3
    content = repository.get_document_content(scene.id)
    assert content[0].plain_text == "one two three"


def test_search_nodes_matches_title_synopsis_and_tags(repository: ManuscriptRepository) -> None:
    root = _node(title="Root")
    repository.add_node(root)
    chapter = _node(
        manuscript_id=root.id,
        parent_id=root.id,
        node_type=ManuscriptNodeType.CHAPTER,
        title="Dragons",
    )
    repository.add_node(chapter)
    repository.update_node(chapter.id, tags=("worldbuilding",))

    by_title = repository.search_nodes("dragon")
    by_tag = repository.search_nodes("worldbuilding")

    assert [n.title for n in by_title] == ["Dragons"]
    assert [n.title for n in by_tag] == ["Dragons"]


def test_search_content_matches_document_body(repository: ManuscriptRepository) -> None:
    root = _node()
    repository.add_node(root)
    scene = _node(
        manuscript_id=root.id, parent_id=root.id, node_type=ManuscriptNodeType.SCENE, title="Sc1"
    )
    repository.add_node(scene)
    repository.save_document_content(scene.id, (paragraph("Elena opened the door."),))

    results = repository.search_content("Elena")

    assert [n.id for n in results] == [scene.id]


def test_snapshot_repository_crud(database: Database) -> None:
    node_repository = ManuscriptRepository(database)
    node = _node(title="Sc1", node_type=ManuscriptNodeType.SCENE)
    node_repository.add_node(node)

    snapshots = SnapshotRepository(database)
    node_id = node.id
    snapshot = Snapshot(
        id=uuid4(),
        node_id=node_id,
        created_at=datetime.now(UTC),
        content=(paragraph("hello"),),
        plain_text="hello",
        word_count=1,
        content_hash="abc123",
        name="First",
    )

    snapshots.add(snapshot)

    assert [s.name for s in snapshots.list_for_node(node_id)] == ["First"]
    assert snapshots.get(snapshot.id) is not None
    assert snapshots.delete(snapshot.id) is True
    assert snapshots.list_for_node(node_id) == []


def test_progress_repository_accumulates_same_day_deltas(database: Database) -> None:
    node_repository = ManuscriptRepository(database)
    manuscript = _node(title="Novel")
    node_repository.add_node(manuscript)

    progress = ProgressRepository(database)
    manuscript_id = manuscript.id
    today = date.today()

    progress.record_delta(manuscript_id, today, 100)
    progress.record_delta(manuscript_id, today, 50)

    entry = progress.get_for_day(manuscript_id, today)
    assert entry is not None
    assert entry.net_word_delta == 150
