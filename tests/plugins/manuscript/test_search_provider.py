from __future__ import annotations

from skrybe_studio.plugins.manuscript.application.document_service import DocumentService
from skrybe_studio.plugins.manuscript.application.hierarchy_service import HierarchyService
from skrybe_studio.plugins.manuscript.application.search_provider import ManuscriptSearchProvider
from skrybe_studio.plugins.manuscript.domain.document_ir import paragraph
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType


def test_search_matches_title(
    hierarchy: HierarchyService, search_provider: ManuscriptSearchProvider
) -> None:
    manuscript = hierarchy.create_manuscript("Dragons of the North")

    results = search_provider.search("dragon")

    assert any(r.entity_id == manuscript.id for r in results)


def test_search_matches_synopsis(
    hierarchy: HierarchyService, search_provider: ManuscriptSearchProvider
) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    chapter = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Ch1")
    hierarchy.update_metadata(chapter.id, synopsis="A tale of ice and fire.")

    results = search_provider.search("ice and fire")

    assert any(r.entity_id == chapter.id for r in results)


def test_search_matches_tags(
    hierarchy: HierarchyService, search_provider: ManuscriptSearchProvider
) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    scene = hierarchy.create_node(manuscript.id, ManuscriptNodeType.SCENE, "Sc1")
    hierarchy.update_metadata(scene.id, tags=("worldbuilding",))

    results = search_provider.search("worldbuilding")

    assert any(r.entity_id == scene.id for r in results)


def test_search_matches_document_body(
    hierarchy: HierarchyService,
    documents: DocumentService,
    search_provider: ManuscriptSearchProvider,
) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    scene = hierarchy.create_node(manuscript.id, ManuscriptNodeType.SCENE, "Sc1")
    documents.save_content(scene.id, (paragraph("Elena opened the door slowly."),))

    results = search_provider.search("Elena")

    assert any(r.entity_id == scene.id for r in results)
    result = next(r for r in results if r.entity_id == scene.id)
    assert "Elena" in result.snippet
    assert result.entity_type == "manuscript.scene"
    assert result.plugin_owner == "com.adeptus-craftmatica.skrybe.manuscript"


def test_search_scoped_by_manuscript_id(
    hierarchy: HierarchyService, search_provider: ManuscriptSearchProvider
) -> None:
    manuscript_a = hierarchy.create_manuscript("Alpha")
    manuscript_b = hierarchy.create_manuscript("Beta")
    hierarchy.create_node(manuscript_a.id, ManuscriptNodeType.CHAPTER, "Shared Title")
    hierarchy.create_node(manuscript_b.id, ManuscriptNodeType.CHAPTER, "Shared Title")

    results = search_provider.search_scoped("Shared Title", manuscript_id=manuscript_a.id)

    assert len(results) == 1


def test_search_does_not_match_archived_nodes(
    hierarchy: HierarchyService, search_provider: ManuscriptSearchProvider
) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    chapter = hierarchy.create_node(manuscript.id, ManuscriptNodeType.CHAPTER, "Findable Chapter")
    hierarchy.archive_node(chapter.id)

    results = search_provider.search("Findable")

    assert not any(r.entity_id == chapter.id for r in results)
