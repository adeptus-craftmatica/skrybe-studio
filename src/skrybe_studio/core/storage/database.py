"""Engine and session management for a single project's SQLite database."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from skrybe_studio.core.storage.base import Base

logger = logging.getLogger(__name__)


def _enable_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Database:
    """Owns the SQLAlchemy engine and session factory for one project.db file."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._engine: Engine = create_engine(f"sqlite:///{db_path}", future=True)
        event.listen(self._engine, "connect", _enable_foreign_keys)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    @property
    def engine(self) -> Engine:
        return self._engine

    @property
    def path(self) -> Path:
        return self._db_path

    def create_core_tables(self) -> None:
        """Create core-owned tables. Plugin tables are created by the migration coordinator."""
        Base.metadata.create_all(self._engine)
        logger.debug("Core tables ensured for %s", self._db_path)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Yield a session bound to an explicit commit/rollback transaction boundary."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        self._engine.dispose()
