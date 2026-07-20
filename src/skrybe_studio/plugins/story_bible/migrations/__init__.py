"""Migrations for the Story Bible plugin's own tables."""

from __future__ import annotations

from sqlalchemy import Engine

from skrybe_studio.core.storage.migration_coordinator import Migration
from skrybe_studio.plugins.story_bible.infrastructure.models import StoryBibleBase


def _create_initial_schema(engine: Engine) -> None:
    StoryBibleBase.metadata.create_all(engine)


def get_migrations() -> list[Migration]:
    return [Migration(name="0001_initial_schema", apply=_create_initial_schema)]
