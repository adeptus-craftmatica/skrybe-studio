from __future__ import annotations

from PySide6.QtCore import QMimeData, Qt

from skrybe_studio.plugins.manuscript.application.hierarchy_service import HierarchyService
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType
from skrybe_studio.plugins.manuscript.ui.binder.model import NODE_MIME_TYPE, ManuscriptTreeModel


def test_model_populates_from_hierarchy(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Ch1")
    hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Ch2")

    model = ManuscriptTreeModel(hierarchy, manuscript.id)

    assert model.rowCount() == 2
    titles = [model.data(model.index(i, 0), Qt.ItemDataRole.EditRole) for i in range(2)]
    assert titles == ["Ch1", "Ch2"]


def test_rename_via_set_data_updates_hierarchy(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Old Title")
    model = ManuscriptTreeModel(hierarchy, manuscript.id)
    index = model.index(0, 0)

    result = model.setData(index, "New Title", Qt.ItemDataRole.EditRole)

    assert result is True
    assert hierarchy.list_children(manuscript.id)[0].title == "New Title"


def test_set_data_rejects_blank_title(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Keep Me")
    model = ManuscriptTreeModel(hierarchy, manuscript.id)
    index = model.index(0, 0)

    result = model.setData(index, "   ", Qt.ItemDataRole.EditRole)

    assert result is False
    assert hierarchy.list_children(manuscript.id)[0].title == "Keep Me"


def test_index_for_node_id_finds_nested_nodes(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    chapter = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Ch1")
    scene = hierarchy.create_node(chapter.id, ManuscriptNodeType.SCENE, "Sc1")
    model = ManuscriptTreeModel(hierarchy, manuscript.id)

    index = model.index_for_node_id(scene.id)

    assert index.isValid()
    found_node = model.node_for_index(index)
    assert found_node is not None
    assert found_node.id == scene.id


def test_node_for_index_returns_none_for_invalid_index(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    model = ManuscriptTreeModel(hierarchy, manuscript.id)

    assert model.node_for_index(model.index(99, 0)) is None


def test_flags_only_allow_drops_on_containers(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    chapter = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Ch1")
    scene = hierarchy.create_node(chapter.id, ManuscriptNodeType.SCENE, "Sc1")
    model = ManuscriptTreeModel(hierarchy, manuscript.id)

    chapter_index = model.index_for_node_id(chapter.id)
    scene_index = model.index_for_node_id(scene.id)

    assert bool(model.flags(chapter_index) & Qt.ItemFlag.ItemIsDropEnabled) is True
    assert bool(model.flags(scene_index) & Qt.ItemFlag.ItemIsDropEnabled) is False


def test_drop_mime_data_moves_node_when_valid(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    folder = hierarchy.create_node(manuscript.id, ManuscriptNodeType.FOLDER, "Folder")
    chapter = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Ch1")
    model = ManuscriptTreeModel(hierarchy, manuscript.id)

    mime = QMimeData()
    mime.setData(NODE_MIME_TYPE, str(chapter.id).encode("utf-8"))
    folder_index = model.index_for_node_id(folder.id)

    accepted = model.dropMimeData(mime, Qt.DropAction.MoveAction, -1, 0, folder_index)

    assert accepted is True
    moved_chapter = hierarchy.get_node(chapter.id)
    assert moved_chapter is not None
    assert moved_chapter.parent_id == folder.id


def test_drop_mime_data_rejects_invalid_move(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    chapter_a = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "A")
    chapter_b = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "B")
    model = ManuscriptTreeModel(hierarchy, manuscript.id)

    mime = QMimeData()
    mime.setData(NODE_MIME_TYPE, str(chapter_a.id).encode("utf-8"))
    target_index = model.index_for_node_id(chapter_b.id)

    accepted = model.dropMimeData(mime, Qt.DropAction.MoveAction, -1, 0, target_index)

    assert accepted is False
    unmoved_chapter = hierarchy.get_node(chapter_a.id)
    assert unmoved_chapter is not None
    assert unmoved_chapter.parent_id == manuscript.id


def test_drop_mime_data_rejects_data_without_the_expected_format(
    hierarchy: HierarchyService,
) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    folder = hierarchy.create_node(manuscript.id, ManuscriptNodeType.FOLDER, "Folder")
    model = ManuscriptTreeModel(hierarchy, manuscript.id)

    mime = QMimeData()
    mime.setText("not the right format")
    folder_index = model.index_for_node_id(folder.id)

    assert model.canDropMimeData(mime, Qt.DropAction.MoveAction, -1, 0, folder_index) is False
