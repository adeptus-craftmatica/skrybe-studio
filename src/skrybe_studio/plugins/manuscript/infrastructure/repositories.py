"""Persistence for manuscript nodes, document content, snapshots, and daily progress.

The application layer never touches SQL directly - everything goes
through these repositories.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select

from skrybe_studio.core.storage.database import Database
from skrybe_studio.plugins.manuscript.domain.document_ir import (
    DocumentContent,
    deserialize_document,
    document_plain_text,
    serialize_document,
)
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType, NodeStatus
from skrybe_studio.plugins.manuscript.domain.models import DailyProgress, ManuscriptNode, Snapshot
from skrybe_studio.plugins.manuscript.domain.word_count import count_words
from skrybe_studio.plugins.manuscript.infrastructure.models import (
    ManuscriptDailyProgressRecord,
    ManuscriptDocumentContentRecord,
    ManuscriptNodeRecord,
    ManuscriptSnapshotRecord,
)

# Fractional sort keys: inserting between two siblings never requires
# renumbering any other row. When there's no neighbor on one side, step by
# this amount so there's headroom for future inserts on that side too.
_SORT_STEP = 1024.0


def sort_order_between(before: float | None, after: float | None) -> float:
    if before is None and after is None:
        return _SORT_STEP
    if before is None:
        return after - _SORT_STEP  # type: ignore[operator]
    if after is None:
        return before + _SORT_STEP
    return (before + after) / 2.0


def _node_to_domain(record: ManuscriptNodeRecord) -> ManuscriptNode:
    return ManuscriptNode(
        id=record.id,
        manuscript_id=record.manuscript_id,
        parent_id=record.parent_id,
        node_type=ManuscriptNodeType(record.node_type),
        title=record.title,
        sort_order=record.sort_order,
        created_at=record.created_at,
        updated_at=record.updated_at,
        synopsis=record.synopsis,
        status=NodeStatus(record.status),
        label=record.label,
        icon_id=record.icon_id,
        include_in_compile=record.include_in_compile,
        tags=tuple(record.tags_json or []),
        target_word_count=record.target_word_count,
        word_count=record.word_count,
        metadata=dict(record.metadata_json or {}),
        archived_at=record.archived_at,
    )


class ManuscriptRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    # --- node CRUD -----------------------------------------------------------

    def add_node(self, node: ManuscriptNode) -> None:
        with self._database.session() as session:
            session.add(
                ManuscriptNodeRecord(
                    id=node.id,
                    manuscript_id=node.manuscript_id,
                    parent_id=node.parent_id,
                    node_type=node.node_type.value,
                    title=node.title,
                    sort_order=node.sort_order,
                    synopsis=node.synopsis,
                    status=node.status.value,
                    label=node.label,
                    icon_id=node.icon_id,
                    include_in_compile=node.include_in_compile,
                    tags_json=list(node.tags),
                    target_word_count=node.target_word_count,
                    word_count=node.word_count,
                    metadata_json=dict(node.metadata),
                    created_at=node.created_at,
                    updated_at=node.updated_at,
                    archived_at=node.archived_at,
                )
            )

    def get_node(self, node_id: UUID) -> ManuscriptNode | None:
        with self._database.session() as session:
            record = session.get(ManuscriptNodeRecord, node_id)
            return _node_to_domain(record) if record is not None else None

    def get_parent_id(self, node_id: UUID) -> UUID | None:
        with self._database.session() as session:
            record = session.get(ManuscriptNodeRecord, node_id)
            return record.parent_id if record is not None else None

    def list_manuscripts(self, *, include_archived: bool = False) -> list[ManuscriptNode]:
        with self._database.session() as session:
            stmt = select(ManuscriptNodeRecord).where(ManuscriptNodeRecord.parent_id.is_(None))
            if not include_archived:
                stmt = stmt.where(ManuscriptNodeRecord.archived_at.is_(None))
            stmt = stmt.order_by(ManuscriptNodeRecord.sort_order)
            return [_node_to_domain(record) for record in session.scalars(stmt)]

    def list_children(
        self, parent_id: UUID, *, include_archived: bool = False
    ) -> list[ManuscriptNode]:
        with self._database.session() as session:
            stmt = select(ManuscriptNodeRecord).where(ManuscriptNodeRecord.parent_id == parent_id)
            if not include_archived:
                stmt = stmt.where(ManuscriptNodeRecord.archived_at.is_(None))
            stmt = stmt.order_by(ManuscriptNodeRecord.sort_order)
            return [_node_to_domain(record) for record in session.scalars(stmt)]

    def last_child_sort_order(self, parent_id: UUID | None) -> float | None:
        with self._database.session() as session:
            stmt = (
                select(ManuscriptNodeRecord.sort_order)
                .where(ManuscriptNodeRecord.parent_id == parent_id)
                .order_by(ManuscriptNodeRecord.sort_order.desc())
                .limit(1)
            )
            return session.scalars(stmt).first()

    def list_subtree(
        self, node_id: UUID, *, include_archived: bool = False
    ) -> list[ManuscriptNode]:
        """Node plus every descendant, breadth-first. Small trees only (no CTE)."""
        root = self.get_node(node_id)
        if root is None:
            return []
        collected = [root]
        frontier = [node_id]
        while frontier:
            next_frontier: list[UUID] = []
            for parent_id in frontier:
                children = self.list_children(parent_id, include_archived=True)
                for child in children:
                    if not include_archived and child.is_archived and child.id != node_id:
                        continue
                    collected.append(child)
                    next_frontier.append(child.id)
            frontier = next_frontier
        return collected

    def update_node(
        self,
        node_id: UUID,
        *,
        title: str | None = None,
        synopsis: str | None = None,
        status: NodeStatus | None = None,
        label: str | None = None,
        icon_id: str | None = None,
        include_in_compile: bool | None = None,
        tags: tuple[str, ...] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ManuscriptNode | None:
        with self._database.session() as session:
            record = session.get(ManuscriptNodeRecord, node_id)
            if record is None:
                return None
            if title is not None:
                record.title = title
            if synopsis is not None:
                record.synopsis = synopsis
            if status is not None:
                record.status = status.value
            if label is not None:
                record.label = label
            if icon_id is not None:
                record.icon_id = icon_id
            if include_in_compile is not None:
                record.include_in_compile = include_in_compile
            if tags is not None:
                record.tags_json = list(tags)
            if metadata is not None:
                record.metadata_json = metadata
            record.updated_at = datetime.now(UTC)
            session.flush()
            return _node_to_domain(record)

    def set_target_word_count(self, node_id: UUID, target: int | None) -> ManuscriptNode | None:
        """A dedicated setter (rather than folding into `update_node`) because `None`
        is a meaningful value here - "no target" - not "leave unchanged"."""
        with self._database.session() as session:
            record = session.get(ManuscriptNodeRecord, node_id)
            if record is None:
                return None
            record.target_word_count = target
            record.updated_at = datetime.now(UTC)
            session.flush()
            return _node_to_domain(record)

    def move_node(self, node_id: UUID, new_parent_id: UUID, new_sort_order: float) -> bool:
        with self._database.session() as session:
            record = session.get(ManuscriptNodeRecord, node_id)
            if record is None:
                return False
            record.parent_id = new_parent_id
            record.sort_order = new_sort_order
            record.updated_at = datetime.now(UTC)
            return True

    def set_sort_order(self, node_id: UUID, sort_order: float) -> bool:
        with self._database.session() as session:
            record = session.get(ManuscriptNodeRecord, node_id)
            if record is None:
                return False
            record.sort_order = sort_order
            record.updated_at = datetime.now(UTC)
            return True

    def set_archived(self, node_ids: list[UUID], archived_at: datetime | None) -> None:
        if not node_ids:
            return
        with self._database.session() as session:
            for node_id in node_ids:
                record = session.get(ManuscriptNodeRecord, node_id)
                if record is not None:
                    record.archived_at = archived_at
                    record.updated_at = datetime.now(UTC)

    # --- document content -----------------------------------------------------

    def get_document_content(self, node_id: UUID) -> DocumentContent:
        with self._database.session() as session:
            record = session.get(ManuscriptDocumentContentRecord, node_id)
            if record is None:
                return ()
            return deserialize_document(record.content_json)

    def save_document_content(self, node_id: UUID, content: DocumentContent) -> int:
        """Persists content and refreshes the node's cached word count. Returns the new count."""
        plain_text = document_plain_text(content)
        word_count = count_words(plain_text)
        now = datetime.now(UTC)
        with self._database.session() as session:
            record = session.get(ManuscriptDocumentContentRecord, node_id)
            if record is None:
                record = ManuscriptDocumentContentRecord(node_id=node_id)
                session.add(record)
            record.content_json = serialize_document(content)
            record.plain_text = plain_text
            record.updated_at = now

            node_record = session.get(ManuscriptNodeRecord, node_id)
            if node_record is not None:
                node_record.word_count = word_count
                node_record.updated_at = now
        return word_count

    # --- search -----------------------------------------------------------------

    def search_nodes(
        self, query: str, *, manuscript_id: UUID | None = None
    ) -> list[ManuscriptNode]:
        like = f"%{query}%"
        with self._database.session() as session:
            stmt = select(ManuscriptNodeRecord).where(
                ManuscriptNodeRecord.archived_at.is_(None),
                or_(
                    ManuscriptNodeRecord.title.ilike(like),
                    ManuscriptNodeRecord.synopsis.ilike(like),
                    ManuscriptNodeRecord.label.ilike(like),
                ),
            )
            if manuscript_id is not None:
                stmt = stmt.where(ManuscriptNodeRecord.manuscript_id == manuscript_id)
            nodes = [_node_to_domain(record) for record in session.scalars(stmt)]

            needle = query.lower()
            for record in session.scalars(
                select(ManuscriptNodeRecord).where(ManuscriptNodeRecord.archived_at.is_(None))
            ):
                if any(needle in tag.lower() for tag in (record.tags_json or [])):
                    node = _node_to_domain(record)
                    if node.id not in {n.id for n in nodes}:
                        nodes.append(node)
            return nodes

    def search_content(
        self, query: str, *, manuscript_id: UUID | None = None
    ) -> list[ManuscriptNode]:
        like = f"%{query}%"
        with self._database.session() as session:
            stmt = (
                select(ManuscriptNodeRecord)
                .join(
                    ManuscriptDocumentContentRecord,
                    ManuscriptDocumentContentRecord.node_id == ManuscriptNodeRecord.id,
                )
                .where(
                    ManuscriptNodeRecord.archived_at.is_(None),
                    ManuscriptDocumentContentRecord.plain_text.ilike(like),
                )
            )
            if manuscript_id is not None:
                stmt = stmt.where(ManuscriptNodeRecord.manuscript_id == manuscript_id)
            return [_node_to_domain(record) for record in session.scalars(stmt)]

    def content_snippet(self, node_id: UUID, query: str, *, context_chars: int = 60) -> str:
        with self._database.session() as session:
            record = session.get(ManuscriptDocumentContentRecord, node_id)
            if record is None:
                return ""
            text = record.plain_text
            index = text.lower().find(query.lower())
            if index == -1:
                return text[: context_chars * 2].strip()
            start = max(0, index - context_chars)
            end = min(len(text), index + len(query) + context_chars)
            prefix = "…" if start > 0 else ""
            suffix = "…" if end < len(text) else ""
            return f"{prefix}{text[start:end].strip()}{suffix}"


class SnapshotRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def add(self, snapshot: Snapshot) -> None:
        with self._database.session() as session:
            session.add(
                ManuscriptSnapshotRecord(
                    id=snapshot.id,
                    node_id=snapshot.node_id,
                    created_at=snapshot.created_at,
                    name=snapshot.name,
                    note=snapshot.note,
                    content_json=serialize_document(snapshot.content),
                    plain_text=snapshot.plain_text,
                    word_count=snapshot.word_count,
                    content_hash=snapshot.content_hash,
                )
            )

    def list_for_node(self, node_id: UUID) -> list[Snapshot]:
        with self._database.session() as session:
            stmt = (
                select(ManuscriptSnapshotRecord)
                .where(ManuscriptSnapshotRecord.node_id == node_id)
                .order_by(ManuscriptSnapshotRecord.created_at.desc())
            )
            return [_snapshot_to_domain(record) for record in session.scalars(stmt)]

    def get(self, snapshot_id: UUID) -> Snapshot | None:
        with self._database.session() as session:
            record = session.get(ManuscriptSnapshotRecord, snapshot_id)
            return _snapshot_to_domain(record) if record is not None else None

    def delete(self, snapshot_id: UUID) -> bool:
        with self._database.session() as session:
            record = session.get(ManuscriptSnapshotRecord, snapshot_id)
            if record is None:
                return False
            session.delete(record)
            return True


def _snapshot_to_domain(record: ManuscriptSnapshotRecord) -> Snapshot:
    return Snapshot(
        id=record.id,
        node_id=record.node_id,
        created_at=record.created_at,
        content=deserialize_document(record.content_json),
        plain_text=record.plain_text,
        word_count=record.word_count,
        content_hash=record.content_hash,
        name=record.name,
        note=record.note,
    )


class ProgressRepository:
    """Tracks a per-manuscript, per-day net word-count delta.

    Deliberately minimal (see `docs/manuscript-plugin.md`): this is the sum
    of every save's (new_count - old_count) for documents in the
    manuscript on that calendar day, not a true "words newly written"
    count - large deletions elsewhere on the same day can offset new
    writing in the total.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    def record_delta(self, manuscript_id: UUID, day: date, delta: int) -> None:
        if delta == 0:
            return
        with self._database.session() as session:
            stmt = select(ManuscriptDailyProgressRecord).where(
                ManuscriptDailyProgressRecord.manuscript_id == manuscript_id,
                ManuscriptDailyProgressRecord.day == day,
            )
            record = session.scalars(stmt).first()
            if record is None:
                record = ManuscriptDailyProgressRecord(
                    manuscript_id=manuscript_id,
                    day=day,
                    net_word_delta=0,
                    updated_at=datetime.now(UTC),
                )
                session.add(record)
            record.net_word_delta += delta
            record.updated_at = datetime.now(UTC)

    def get_for_day(self, manuscript_id: UUID, day: date) -> DailyProgress | None:
        with self._database.session() as session:
            stmt = select(ManuscriptDailyProgressRecord).where(
                ManuscriptDailyProgressRecord.manuscript_id == manuscript_id,
                ManuscriptDailyProgressRecord.day == day,
            )
            record = session.scalars(stmt).first()
            if record is None:
                return None
            return DailyProgress(
                manuscript_id=record.manuscript_id,
                date=record.day,
                net_word_delta=record.net_word_delta,
                updated_at=record.updated_at,
            )

    def list_recent(self, manuscript_id: UUID, *, limit: int = 30) -> list[DailyProgress]:
        with self._database.session() as session:
            stmt = (
                select(ManuscriptDailyProgressRecord)
                .where(ManuscriptDailyProgressRecord.manuscript_id == manuscript_id)
                .order_by(ManuscriptDailyProgressRecord.day.desc())
                .limit(limit)
            )
            return [
                DailyProgress(
                    manuscript_id=record.manuscript_id,
                    date=record.day,
                    net_word_delta=record.net_word_delta,
                    updated_at=record.updated_at,
                )
                for record in session.scalars(stmt)
            ]
