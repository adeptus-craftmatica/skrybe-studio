from __future__ import annotations

from skrybe_studio.plugins.manuscript.application.document_service import DocumentService
from skrybe_studio.plugins.manuscript.application.goals_service import GoalsService
from skrybe_studio.plugins.manuscript.application.hierarchy_service import HierarchyService
from skrybe_studio.plugins.manuscript.domain.document_ir import paragraph
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType


def test_per_node_target_is_set_and_read_back(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    scene = hierarchy.create_node(manuscript.id, ManuscriptNodeType.SCENE, "Sc1")

    hierarchy.set_target_word_count(scene.id, 500)

    node = hierarchy.get_node(scene.id)
    assert node is not None
    assert node.target_word_count == 500


def test_target_can_be_cleared_back_to_none(hierarchy: HierarchyService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    hierarchy.set_target_word_count(manuscript.id, 50000)

    hierarchy.set_target_word_count(manuscript.id, None)

    node = hierarchy.get_node(manuscript.id)
    assert node is not None
    assert node.target_word_count is None


def test_daily_target_defaults_to_none_and_can_be_set(
    hierarchy: HierarchyService, goals: GoalsService
) -> None:
    manuscript = hierarchy.create_manuscript("Novel")

    assert goals.get_daily_target(manuscript.id) is None

    goals.set_daily_target(manuscript.id, 750)

    assert goals.get_daily_target(manuscript.id) == 750


def test_daily_target_can_be_cleared(hierarchy: HierarchyService, goals: GoalsService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    goals.set_daily_target(manuscript.id, 750)

    goals.set_daily_target(manuscript.id, None)

    assert goals.get_daily_target(manuscript.id) is None


def test_today_progress_reflects_saved_content(
    hierarchy: HierarchyService, documents: DocumentService, goals: GoalsService
) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    scene = hierarchy.create_node(manuscript.id, ManuscriptNodeType.SCENE, "Sc1")

    assert goals.today_progress(manuscript.id) is None

    documents.save_content(scene.id, (paragraph("one two three"),))

    progress = goals.today_progress(manuscript.id)
    assert progress is not None
    assert progress.net_word_delta == 3
