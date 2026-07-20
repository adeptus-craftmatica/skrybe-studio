from __future__ import annotations

import pytest

from skrybe_studio.core.entities.service import EntityService
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.manuscript.application.events import (
    ManuscriptCreated,
    NodeArchived,
    NodeCreated,
    NodeMoved,
    NodeRenamed,
    NodeRestored,
)
from skrybe_studio.plugins.manuscript.application.hierarchy_service import HierarchyService
from skrybe_studio.plugins.manuscript.application.templates import ManuscriptTemplate
from skrybe_studio.plugins.manuscript.domain.document_ir import paragraph
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType
from skrybe_studio.plugins.manuscript.domain.exceptions import (
    CyclicHierarchyError,
    InvalidHierarchyError,
)


def test_create_manuscript_publishes_event_and_creates_entity(
    hierarchy: HierarchyService, entities: EntityService, events: EventBus
) -> None:
    received: list[str] = []
    events.subscribe(ManuscriptCreated, lambda event: received.append(event.title))

    manuscript = hierarchy.create_manuscript("My Novel")

    assert received == ["My Novel"]
    entity = entities.get(manuscript.id)
    assert entity is not None
    assert entity.entity_type == "manuscript.project"


def test_create_manuscript_with_three_act_template_builds_hierarchy(
    hierarchy: HierarchyService,
) -> None:
    manuscript = hierarchy.create_manuscript("My Novel", ManuscriptTemplate.THREE_ACT_NOVEL)

    parts = hierarchy.list_children(manuscript.id)
    assert [p.node_type for p in parts] == [ManuscriptNodeType.PART] * 3
    chapters = hierarchy.list_children(parts[0].id)
    assert chapters[0].node_type == ManuscriptNodeType.CHAPTER
    scenes = hierarchy.list_children(chapters[0].id)
    assert scenes[0].node_type == ManuscriptNodeType.SCENE


def test_create_node_publishes_event_and_creates_entity(
    hierarchy: HierarchyService, entities: EntityService, events: EventBus
) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    received: list[NodeCreated] = []
    events.subscribe(NodeCreated, received.append)

    chapter = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Chapter One")

    assert len(received) == 1
    assert received[0].node_id == chapter.id
    assert entities.get(chapter.id) is not None


def test_create_node_rejects_invalid_child_type(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    chapter = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Chapter One")
    scene = hierarchy.create_node(chapter.id, ManuscriptNodeType.SCENE, "Scene One")

    with pytest.raises(InvalidHierarchyError):
        hierarchy.create_node(scene.id, ManuscriptNodeType.SCENE, "Nested Scene")


def test_rename_node_renames_shared_entity_too(
    hierarchy: HierarchyService, entities: EntityService, events: EventBus
) -> None:
    manuscript = hierarchy.create_manuscript("Old Title")
    received: list[NodeRenamed] = []
    events.subscribe(NodeRenamed, received.append)

    hierarchy.rename_node(manuscript.id, "New Title")

    entity = entities.get(manuscript.id)
    assert entity is not None
    assert entity.title == "New Title"
    assert received[0].title == "New Title"


def test_move_node_rejects_invalid_target_type(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    chapter_a = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "A")
    chapter_b = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "B")

    with pytest.raises(InvalidHierarchyError):
        hierarchy.move_node(chapter_a.id, chapter_b.id)  # a chapter cannot contain a chapter


def test_move_node_rejects_cyclic_move(hierarchy: HierarchyService) -> None:
    # A folder can validly contain another folder, so this scenario is
    # type-valid - it must be rejected specifically for being cyclic.
    manuscript = hierarchy.create_manuscript("Novel")
    outer_folder = hierarchy.create_node(manuscript.id, ManuscriptNodeType.FOLDER, "Outer")
    inner_folder = hierarchy.create_node(outer_folder.id, ManuscriptNodeType.FOLDER, "Inner")

    with pytest.raises(CyclicHierarchyError):
        hierarchy.move_node(outer_folder.id, inner_folder.id)


def test_move_node_publishes_event_and_updates_parent(
    hierarchy: HierarchyService, events: EventBus
) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    folder = hierarchy.create_node(manuscript.id, ManuscriptNodeType.FOLDER, "Folder")
    chapter = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Ch1")
    received: list[NodeMoved] = []
    events.subscribe(NodeMoved, received.append)

    moved = hierarchy.move_node(chapter.id, folder.id)

    assert moved.parent_id == folder.id
    assert received[0].new_parent_id == folder.id


def test_move_sibling_reorders_within_parent(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "First")
    second = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Second")

    hierarchy.move_sibling(second.id, direction=-1)

    children = hierarchy.list_children(manuscript.id)
    assert [c.title for c in children] == ["Second", "First"]


def test_archive_cascades_and_is_recoverable(hierarchy: HierarchyService, events: EventBus) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    chapter = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Ch1")
    scene = hierarchy.create_node(chapter.id, ManuscriptNodeType.SCENE, "Sc1")
    archived_received: list[NodeArchived] = []
    restored_received: list[NodeRestored] = []
    events.subscribe(NodeArchived, archived_received.append)
    events.subscribe(NodeRestored, restored_received.append)

    affected = hierarchy.archive_node(chapter.id)
    assert set(affected) == {chapter.id, scene.id}
    assert hierarchy.list_children(manuscript.id) == []

    restored = hierarchy.restore_node(chapter.id)
    assert set(restored) == {chapter.id, scene.id}
    assert [c.id for c in hierarchy.list_children(manuscript.id)] == [chapter.id]
    assert len(archived_received) == 1
    assert len(restored_received) == 1


def test_duplicate_node_copies_content_but_not_descendants(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    chapter = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Ch1")
    hierarchy.create_node(chapter.id, ManuscriptNodeType.SCENE, "Sc1")

    duplicate = hierarchy.duplicate_node(chapter.id)

    assert duplicate is not None
    assert duplicate.title == "Ch1 Copy"
    assert hierarchy.list_children(duplicate.id) == []  # shallow duplicate


def test_subtree_word_count_sums_text_bearing_descendants(
    hierarchy: HierarchyService, documents
) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    chapter = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Ch1")
    scene_a = hierarchy.create_node(chapter.id, ManuscriptNodeType.SCENE, "Sc1")
    scene_b = hierarchy.create_node(chapter.id, ManuscriptNodeType.SCENE, "Sc2")

    documents.save_content(scene_a.id, (paragraph("one two three"),))
    documents.save_content(scene_b.id, (paragraph("four five"),))

    assert hierarchy.subtree_word_count(chapter.id) == 5
    assert hierarchy.subtree_word_count(manuscript.id) == 5


def test_subtree_word_count_respects_compile_flag(hierarchy: HierarchyService, documents) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    scene = hierarchy.create_node(manuscript.id, ManuscriptNodeType.SCENE, "Sc1")
    documents.save_content(scene.id, (paragraph("one two three"),))
    hierarchy.update_metadata(scene.id, include_in_compile=False)

    assert hierarchy.subtree_word_count(manuscript.id, respect_compile_flag=True) == 0
    assert hierarchy.subtree_word_count(manuscript.id, respect_compile_flag=False) == 3


def test_list_subtree_excludes_archived_nodes(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    chapter = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Ch1")
    hierarchy.archive_node(chapter.id)

    subtree = hierarchy.list_subtree(manuscript.id)

    assert chapter.id not in {n.id for n in subtree}
