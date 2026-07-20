"""Persistence for `Note`s. The application layer never touches SQL directly."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select

from skrybe_studio.core.storage.database import Database
from skrybe_studio.plugins.notes.domain.note import Note
from skrybe_studio.plugins.notes.infrastructure.models import NoteRecord


def _to_note(record: NoteRecord) -> Note:
    return Note(
        id=record.id,
        title=record.title,
        body=record.body,
        tags=tuple(record.tags_json or []),
        created_at=record.created_at,
        updated_at=record.updated_at,
        archived_at=record.archived_at,
    )


class NoteRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def add(self, note: Note) -> None:
        with self._database.session() as session:
            session.add(
                NoteRecord(
                    id=note.id,
                    title=note.title,
                    body=note.body,
                    tags_json=list(note.tags),
                    created_at=note.created_at,
                    updated_at=note.updated_at,
                    archived_at=note.archived_at,
                )
            )

    def get(self, note_id: UUID) -> Note | None:
        with self._database.session() as session:
            record = session.get(NoteRecord, note_id)
            return _to_note(record) if record is not None else None

    def list(self, *, include_archived: bool = False) -> list[Note]:
        with self._database.session() as session:
            stmt = select(NoteRecord).order_by(NoteRecord.updated_at.desc())
            if not include_archived:
                stmt = stmt.where(NoteRecord.archived_at.is_(None))
            return [_to_note(record) for record in session.scalars(stmt)]

    def update(
        self,
        note_id: UUID,
        *,
        title: str | None = None,
        body: str | None = None,
        tags: tuple[str, ...] | None = None,
    ) -> Note | None:
        with self._database.session() as session:
            record = session.get(NoteRecord, note_id)
            if record is None:
                return None
            if title is not None:
                record.title = title
            if body is not None:
                record.body = body
            if tags is not None:
                record.tags_json = list(tags)
            record.updated_at = datetime.now(UTC)
            session.flush()
            return _to_note(record)

    def archive(self, note_id: UUID) -> bool:
        with self._database.session() as session:
            record = session.get(NoteRecord, note_id)
            if record is None:
                return False
            record.archived_at = datetime.now(UTC)
            return True

    def delete(self, note_id: UUID) -> bool:
        with self._database.session() as session:
            record = session.get(NoteRecord, note_id)
            if record is None:
                return False
            session.delete(record)
            return True

    def search(self, query: str) -> list[Note]:
        like = f"%{query}%"
        with self._database.session() as session:
            stmt = select(NoteRecord).where(
                NoteRecord.archived_at.is_(None),
                or_(NoteRecord.title.ilike(like), NoteRecord.body.ilike(like)),
            )
            return [_to_note(record) for record in session.scalars(stmt)]
