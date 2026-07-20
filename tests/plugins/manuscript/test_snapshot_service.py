from __future__ import annotations

from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.manuscript.application.diff import DiffLineKind
from skrybe_studio.plugins.manuscript.application.document_service import DocumentService
from skrybe_studio.plugins.manuscript.application.events import SnapshotCreated, SnapshotRestored
from skrybe_studio.plugins.manuscript.application.hierarchy_service import HierarchyService
from skrybe_studio.plugins.manuscript.application.snapshot_service import (
    SAFETY_SNAPSHOT_NAME,
    SnapshotService,
)
from skrybe_studio.plugins.manuscript.domain.document_ir import paragraph
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType


def _scene(hierarchy: HierarchyService):
    manuscript = hierarchy.create_manuscript("Novel")
    return hierarchy.create_node(manuscript.id, ManuscriptNodeType.SCENE, "Sc1")


def test_create_snapshot_captures_current_content_and_publishes_event(
    hierarchy: HierarchyService,
    documents: DocumentService,
    snapshots: SnapshotService,
    events: EventBus,
) -> None:
    scene = _scene(hierarchy)
    documents.save_content(scene.id, (paragraph("draft one"),))
    received: list[SnapshotCreated] = []
    events.subscribe(SnapshotCreated, received.append)

    snapshot = snapshots.create_snapshot(scene.id, name="First Draft")

    assert snapshot.plain_text == "draft one"
    assert snapshot.word_count == 2
    assert received[0].node_id == scene.id


def test_list_snapshots_returns_newest_first(
    hierarchy: HierarchyService, documents: DocumentService, snapshots: SnapshotService
) -> None:
    scene = _scene(hierarchy)
    documents.save_content(scene.id, (paragraph("v1"),))
    snapshots.create_snapshot(scene.id, name="v1")
    documents.save_content(scene.id, (paragraph("v2"),))
    snapshots.create_snapshot(scene.id, name="v2")

    names = [s.name for s in snapshots.list_snapshots(scene.id)]

    assert names == ["v2", "v1"]


def test_diff_against_current_reports_insertions(
    hierarchy: HierarchyService, documents: DocumentService, snapshots: SnapshotService
) -> None:
    scene = _scene(hierarchy)
    documents.save_content(scene.id, (paragraph("line one"),))
    snapshot = snapshots.create_snapshot(scene.id)
    documents.save_content(scene.id, (paragraph("line one"), paragraph("line two")))

    diff = snapshots.diff_against_current(snapshot.id)

    assert diff is not None
    kinds = [line.kind for line in diff]
    assert DiffLineKind.INSERT in kinds
    assert DiffLineKind.EQUAL in kinds


def test_restore_snapshot_creates_safety_snapshot_first(
    hierarchy: HierarchyService,
    documents: DocumentService,
    snapshots: SnapshotService,
    events: EventBus,
) -> None:
    scene = _scene(hierarchy)
    documents.save_content(scene.id, (paragraph("original"),))
    original_snapshot = snapshots.create_snapshot(scene.id, name="Original")
    documents.save_content(scene.id, (paragraph("changed"),))
    received: list[SnapshotRestored] = []
    events.subscribe(SnapshotRestored, received.append)

    restored = snapshots.restore_snapshot(original_snapshot.id)

    assert restored is True
    assert documents.load_content(scene.id)[0].plain_text == "original"
    all_snapshots = snapshots.list_snapshots(scene.id)
    assert any(s.name == SAFETY_SNAPSHOT_NAME for s in all_snapshots)
    assert received[0].snapshot_id == original_snapshot.id


def test_delete_snapshot(
    hierarchy: HierarchyService, documents: DocumentService, snapshots: SnapshotService
) -> None:
    scene = _scene(hierarchy)
    documents.save_content(scene.id, (paragraph("draft"),))
    snapshot = snapshots.create_snapshot(scene.id)

    assert snapshots.delete_snapshot(snapshot.id) is True
    assert snapshots.list_snapshots(scene.id) == []


def test_restore_unknown_snapshot_returns_false(snapshots: SnapshotService) -> None:
    from uuid import uuid4

    assert snapshots.restore_snapshot(uuid4()) is False
