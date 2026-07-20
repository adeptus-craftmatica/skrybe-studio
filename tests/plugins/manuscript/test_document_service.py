from __future__ import annotations

from datetime import UTC, datetime

from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.manuscript.application.document_service import DocumentService
from skrybe_studio.plugins.manuscript.application.events import DocumentContentChanged
from skrybe_studio.plugins.manuscript.application.hierarchy_service import HierarchyService
from skrybe_studio.plugins.manuscript.domain.document_ir import paragraph
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType
from skrybe_studio.plugins.manuscript.infrastructure.repositories import ProgressRepository


def test_save_content_publishes_event_with_word_count(
    hierarchy: HierarchyService, documents: DocumentService, events: EventBus
) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    scene = hierarchy.create_node(manuscript.id, ManuscriptNodeType.SCENE, "Sc1")
    received: list[DocumentContentChanged] = []
    events.subscribe(DocumentContentChanged, received.append)

    word_count = documents.save_content(scene.id, (paragraph("one two three four"),))

    assert word_count == 4
    assert received[0].node_id == scene.id
    assert received[0].word_count == 4


def test_load_content_round_trips(hierarchy: HierarchyService, documents: DocumentService) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    scene = hierarchy.create_node(manuscript.id, ManuscriptNodeType.SCENE, "Sc1")
    documents.save_content(scene.id, (paragraph("hello world"),))

    content = documents.load_content(scene.id)

    assert content[0].plain_text == "hello world"


def test_save_content_records_daily_progress_delta(
    hierarchy: HierarchyService, documents: DocumentService, progress_repository: ProgressRepository
) -> None:
    manuscript = hierarchy.create_manuscript("Novel")
    scene = hierarchy.create_node(manuscript.id, ManuscriptNodeType.SCENE, "Sc1")

    documents.save_content(scene.id, (paragraph("one two three"),))
    documents.save_content(scene.id, (paragraph("one two three four five"),))

    today = datetime.now(UTC).date()
    entry = progress_repository.get_for_day(manuscript.id, today)
    assert entry is not None
    assert entry.net_word_delta == 5  # +3 then +2
