"""Creates, lists, restores, and deletes document snapshots.

Restoring always takes a safety snapshot of the current content first, so
a restore is itself always recoverable - it never needs its own undo
command.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.manuscript.application.diff import DiffLine, diff_lines
from skrybe_studio.plugins.manuscript.application.document_service import DocumentService
from skrybe_studio.plugins.manuscript.application.events import SnapshotCreated, SnapshotRestored
from skrybe_studio.plugins.manuscript.domain.document_ir import (
    document_plain_text,
    serialize_document,
)
from skrybe_studio.plugins.manuscript.domain.models import Snapshot
from skrybe_studio.plugins.manuscript.domain.word_count import count_words
from skrybe_studio.plugins.manuscript.infrastructure.repositories import SnapshotRepository

logger = logging.getLogger(__name__)

SAFETY_SNAPSHOT_NAME = "Before restore"


class SnapshotService:
    def __init__(
        self, snapshots: SnapshotRepository, documents: DocumentService, events: EventBus
    ) -> None:
        self._snapshots = snapshots
        self._documents = documents
        self._events = events

    def create_snapshot(self, node_id: UUID, *, name: str = "", note: str = "") -> Snapshot:
        content = self._documents.load_content(node_id)
        plain_text = document_plain_text(content)
        content_hash = hashlib.sha256(serialize_document(content).encode("utf-8")).hexdigest()
        snapshot = Snapshot(
            id=uuid4(),
            node_id=node_id,
            created_at=datetime.now(UTC),
            content=content,
            plain_text=plain_text,
            word_count=count_words(plain_text),
            content_hash=content_hash,
            name=name,
            note=note,
        )
        self._snapshots.add(snapshot)
        logger.info("Created snapshot '%s' for node %s", name or snapshot.id, node_id)
        self._events.publish(SnapshotCreated(snapshot_id=snapshot.id, node_id=node_id))
        return snapshot

    def list_snapshots(self, node_id: UUID) -> list[Snapshot]:
        return self._snapshots.list_for_node(node_id)

    def get_snapshot(self, snapshot_id: UUID) -> Snapshot | None:
        return self._snapshots.get(snapshot_id)

    def restore_snapshot(self, snapshot_id: UUID) -> bool:
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            return False
        self.create_snapshot(
            snapshot.node_id,
            name=SAFETY_SNAPSHOT_NAME,
            note="Automatic safety snapshot before restore",
        )
        self._documents.save_content(snapshot.node_id, snapshot.content)
        logger.info("Restored snapshot %s for node %s", snapshot_id, snapshot.node_id)
        self._events.publish(SnapshotRestored(node_id=snapshot.node_id, snapshot_id=snapshot_id))
        return True

    def delete_snapshot(self, snapshot_id: UUID) -> bool:
        return self._snapshots.delete(snapshot_id)

    def diff_against_current(self, snapshot_id: UUID) -> list[DiffLine] | None:
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            return None
        current_text = document_plain_text(self._documents.load_content(snapshot.node_id))
        return diff_lines(snapshot.plain_text, current_text)
