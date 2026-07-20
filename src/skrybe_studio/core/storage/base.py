"""Declarative base for core-owned tables.

Plugins must NOT import this base for their own tables - each plugin
defines its own `DeclarativeBase` subclass (see
`docs/plugin-development.md`) so that core and plugin schemas evolve
independently while still sharing one physical SQLite file.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for tables owned by the core platform."""
