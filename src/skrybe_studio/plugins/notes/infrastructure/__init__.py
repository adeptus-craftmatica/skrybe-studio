"""Notes plugin persistence: its own SQLAlchemy declarative base and repository."""

from skrybe_studio.plugins.notes.infrastructure.repository import NoteRepository

__all__ = ["NoteRepository"]
