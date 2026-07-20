"""Domain models: `ManuscriptNode`, `Snapshot`, `DailyProgress`, and hierarchy validation.

Plain Python only - no Qt, no SQLAlchemy. Persistence lives in
`infrastructure/`; this module is what `infrastructure` and
`application` both build on.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import UUID

from skrybe_studio.plugins.manuscript.domain.document_ir import EMPTY_DOCUMENT, DocumentContent
from skrybe_studio.plugins.manuscript.domain.enums import (
    ALLOWED_CHILD_TYPES,
    TEXT_BEARING_NODE_TYPES,
    ManuscriptNodeType,
    NodeStatus,
)
from skrybe_studio.plugins.manuscript.domain.exceptions import (
    CyclicHierarchyError,
    InvalidHierarchyError,
)

PLUGIN_ID = "com.adeptus-craftmatica.skrybe.manuscript"


def entity_type_for(node_type: ManuscriptNodeType) -> str:
    """The shared `Entity.entity_type` string for a node type, e.g. `"manuscript.scene"`.

    The root MANUSCRIPT node type maps to `"manuscript.project"` rather
    than `"manuscript.manuscript"`, matching the entity-type identifiers
    published in `docs/manuscript-plugin.md`.
    """
    if node_type is ManuscriptNodeType.MANUSCRIPT:
        return "manuscript.project"
    return f"manuscript.{node_type.value}"


def validate_child_type(parent_type: ManuscriptNodeType, child_type: ManuscriptNodeType) -> None:
    """Raises `InvalidHierarchyError` if `child_type` cannot be a child of `parent_type`."""
    allowed = ALLOWED_CHILD_TYPES.get(parent_type, frozenset())
    if child_type not in allowed:
        raise InvalidHierarchyError(
            f"A '{parent_type.value}' cannot contain a '{child_type.value}'"
        )


def would_create_cycle(
    node_id: UUID, new_parent_id: UUID, get_parent_id: Callable[[UUID], UUID | None]
) -> bool:
    """Whether moving `node_id` under `new_parent_id` would make it its own ancestor.

    `get_parent_id` is a lookup callable rather than a repository dependency,
    so this stays pure and testable with a plain dict in unit tests.
    """
    if new_parent_id == node_id:
        return True
    current: UUID | None = new_parent_id
    seen = {new_parent_id}
    while current is not None:
        parent = get_parent_id(current)
        if parent == node_id:
            return True
        if parent is None or parent in seen:
            return False
        seen.add(parent)
        current = parent
    return False


def raise_if_cyclic(
    node_id: UUID, new_parent_id: UUID, get_parent_id: Callable[[UUID], UUID | None]
) -> None:
    if would_create_cycle(node_id, new_parent_id, get_parent_id):
        raise CyclicHierarchyError(f"Moving {node_id} under {new_parent_id} would create a cycle")


@dataclass(frozen=True, slots=True)
class ManuscriptNode:
    """A node in the manuscript binder hierarchy.

    `id` doubles as the shared `Entity` ID. `manuscript_id` is the root
    MANUSCRIPT node's own ID (self-referential for the root) - every node
    carries it so one project database can hold more than one manuscript.
    """

    id: UUID
    manuscript_id: UUID
    parent_id: UUID | None
    node_type: ManuscriptNodeType
    title: str
    sort_order: float
    created_at: datetime
    updated_at: datetime
    synopsis: str = ""
    status: NodeStatus = NodeStatus.DRAFT
    label: str = ""
    icon_id: str | None = None
    include_in_compile: bool = True
    tags: tuple[str, ...] = field(default_factory=tuple)
    target_word_count: int | None = None
    word_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    archived_at: datetime | None = None

    @property
    def is_root(self) -> bool:
        return self.parent_id is None

    @property
    def is_container(self) -> bool:
        return self.node_type not in TEXT_BEARING_NODE_TYPES

    @property
    def is_text_bearing(self) -> bool:
        return self.node_type in TEXT_BEARING_NODE_TYPES

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    @property
    def entity_type(self) -> str:
        return entity_type_for(self.node_type)


@dataclass(frozen=True, slots=True)
class Snapshot:
    id: UUID
    node_id: UUID
    created_at: datetime
    content: DocumentContent
    plain_text: str
    word_count: int
    content_hash: str
    name: str = ""
    note: str = ""


@dataclass(frozen=True, slots=True)
class DailyProgress:
    manuscript_id: UUID
    date: date
    net_word_delta: int
    updated_at: datetime


__all__ = [
    "EMPTY_DOCUMENT",
    "PLUGIN_ID",
    "DailyProgress",
    "ManuscriptNode",
    "Snapshot",
    "entity_type_for",
    "raise_if_cyclic",
    "validate_child_type",
    "would_create_cycle",
]
