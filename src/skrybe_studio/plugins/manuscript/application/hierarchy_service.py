"""Creates, renames, moves, and archives manuscript nodes.

Keeps the shared `Entity` in sync with every node, validates hierarchy
rules before persisting, and publishes events after each change commits.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from skrybe_studio.core.entities.service import EntityService
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.manuscript.application.events import (
    ManuscriptArchived,
    ManuscriptCreated,
    ManuscriptRenamed,
    NodeArchived,
    NodeCreated,
    NodeMetadataChanged,
    NodeMoved,
    NodeRenamed,
    NodeRestored,
)
from skrybe_studio.plugins.manuscript.application.templates import (
    ManuscriptTemplate,
    TemplateNode,
    template_structure,
)
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType, NodeStatus
from skrybe_studio.plugins.manuscript.domain.exceptions import NodeNotFoundError
from skrybe_studio.plugins.manuscript.domain.models import (
    PLUGIN_ID,
    ManuscriptNode,
    entity_type_for,
    raise_if_cyclic,
    validate_child_type,
)
from skrybe_studio.plugins.manuscript.infrastructure.repositories import (
    ManuscriptRepository,
    sort_order_between,
)

logger = logging.getLogger(__name__)


class HierarchyService:
    def __init__(
        self, repository: ManuscriptRepository, entities: EntityService, events: EventBus
    ) -> None:
        self._repository = repository
        self._entities = entities
        self._events = events

    # --- manuscripts -----------------------------------------------------------

    def create_manuscript(
        self, title: str, template: ManuscriptTemplate = ManuscriptTemplate.BLANK
    ) -> ManuscriptNode:
        root = self._create_node_record(
            manuscript_id=None,
            parent_id=None,
            node_type=ManuscriptNodeType.MANUSCRIPT,
            title=title,
        )
        for template_node in template_structure(template):
            self._instantiate_template(template_node, manuscript_id=root.id, parent_id=root.id)
        logger.info(
            "Created manuscript '%s' (%s) from template '%s'", title, root.id, template.value
        )
        self._events.publish(ManuscriptCreated(manuscript_id=root.id, title=title))
        return root

    def _instantiate_template(
        self, template_node: TemplateNode, *, manuscript_id: UUID, parent_id: UUID
    ) -> None:
        node = self._create_node_record(
            manuscript_id=manuscript_id,
            parent_id=parent_id,
            node_type=template_node.node_type,
            title=template_node.title,
        )
        for child in template_node.children:
            self._instantiate_template(child, manuscript_id=manuscript_id, parent_id=node.id)

    def list_manuscripts(self) -> list[ManuscriptNode]:
        return self._repository.list_manuscripts()

    def rename_manuscript(self, manuscript_id: UUID, title: str) -> ManuscriptNode | None:
        node = self.rename_node(manuscript_id, title)
        if node is not None:
            self._events.publish(ManuscriptRenamed(manuscript_id=manuscript_id, title=title))
        return node

    def archive_manuscript(self, manuscript_id: UUID) -> list[UUID]:
        affected = self.archive_node(manuscript_id)
        self._events.publish(ManuscriptArchived(manuscript_id=manuscript_id))
        return affected

    # --- nodes -------------------------------------------------------------------

    def create_node(
        self, parent_id: UUID, node_type: ManuscriptNodeType, title: str
    ) -> ManuscriptNode:
        parent = self._repository.get_node(parent_id)
        if parent is None:
            raise NodeNotFoundError(f"Parent node {parent_id} does not exist")
        validate_child_type(parent.node_type, node_type)
        node = self._create_node_record(
            manuscript_id=parent.manuscript_id,
            parent_id=parent_id,
            node_type=node_type,
            title=title,
        )
        self._events.publish(
            NodeCreated(
                node_id=node.id,
                manuscript_id=node.manuscript_id,
                parent_id=parent_id,
                node_type=node_type.value,
            )
        )
        return node

    def _create_node_record(
        self,
        *,
        manuscript_id: UUID | None,
        parent_id: UUID | None,
        node_type: ManuscriptNodeType,
        title: str,
    ) -> ManuscriptNode:
        now = datetime.now(UTC)
        node_id = uuid4()
        resolved_manuscript_id = manuscript_id if manuscript_id is not None else node_id
        sort_order = sort_order_between(self._repository.last_child_sort_order(parent_id), None)
        node = ManuscriptNode(
            id=node_id,
            manuscript_id=resolved_manuscript_id,
            parent_id=parent_id,
            node_type=node_type,
            title=title,
            sort_order=sort_order,
            created_at=now,
            updated_at=now,
        )
        self._entities.create(
            entity_type=entity_type_for(node_type),
            title=title,
            plugin_owner=PLUGIN_ID,
            entity_id=node_id,
        )
        self._repository.add_node(node)
        return node

    def get_node(self, node_id: UUID) -> ManuscriptNode | None:
        return self._repository.get_node(node_id)

    def list_children(self, parent_id: UUID) -> list[ManuscriptNode]:
        return self._repository.list_children(parent_id)

    def rename_node(self, node_id: UUID, title: str) -> ManuscriptNode | None:
        node = self._repository.update_node(node_id, title=title)
        if node is None:
            return None
        self._entities.rename(node_id, title)
        self._events.publish(NodeRenamed(node_id=node_id, title=title))
        return node

    def update_metadata(
        self,
        node_id: UUID,
        *,
        synopsis: str | None = None,
        status: NodeStatus | None = None,
        label: str | None = None,
        icon_id: str | None = None,
        include_in_compile: bool | None = None,
        tags: tuple[str, ...] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ManuscriptNode | None:
        node = self._repository.update_node(
            node_id,
            synopsis=synopsis,
            status=status,
            label=label,
            icon_id=icon_id,
            include_in_compile=include_in_compile,
            tags=tags,
            metadata=metadata,
        )
        if node is not None:
            self._events.publish(NodeMetadataChanged(node_id=node_id))
        return node

    def set_target_word_count(self, node_id: UUID, target: int | None) -> ManuscriptNode | None:
        node = self._repository.set_target_word_count(node_id, target)
        if node is not None:
            self._events.publish(NodeMetadataChanged(node_id=node_id))
        return node

    def move_node(
        self,
        node_id: UUID,
        new_parent_id: UUID,
        *,
        before_id: UUID | None = None,
        after_id: UUID | None = None,
    ) -> ManuscriptNode:
        """Moves `node_id` to be a child of `new_parent_id`, positioned between
        `before_id` and `after_id` (either or both may be `None` for an edge
        position). Raises `InvalidHierarchyError`/`CyclicHierarchyError` on an
        invalid move - the caller (typically the binder) should catch and
        reject the drop rather than let it persist."""
        node = self._repository.get_node(node_id)
        new_parent = self._repository.get_node(new_parent_id)
        if node is None or new_parent is None:
            raise NodeNotFoundError("Node or new parent does not exist")
        validate_child_type(new_parent.node_type, node.node_type)
        raise_if_cyclic(node_id, new_parent_id, self._repository.get_parent_id)

        before_order = self._sort_order_of(before_id)
        after_order = self._sort_order_of(after_id)
        new_sort_order = sort_order_between(before_order, after_order)
        self._repository.move_node(node_id, new_parent_id, new_sort_order)
        self._events.publish(NodeMoved(node_id=node_id, new_parent_id=new_parent_id))
        updated = self._repository.get_node(node_id)
        assert updated is not None
        return updated

    def reorder_within_parent(
        self, node_id: UUID, *, before_id: UUID | None, after_id: UUID | None
    ) -> ManuscriptNode | None:
        node = self._repository.get_node(node_id)
        if node is None:
            return None
        before_order = self._sort_order_of(before_id)
        after_order = self._sort_order_of(after_id)
        new_sort_order = sort_order_between(before_order, after_order)
        self._repository.set_sort_order(node_id, new_sort_order)
        self._events.publish(NodeMoved(node_id=node_id, new_parent_id=node.parent_id or node_id))
        return self._repository.get_node(node_id)

    def move_sibling(self, node_id: UUID, *, direction: int) -> ManuscriptNode | None:
        """Moves a node up (`direction=-1`) or down (`direction=1`) among its siblings."""
        node = self._repository.get_node(node_id)
        if node is None or node.parent_id is None:
            return None
        siblings = self._repository.list_children(node.parent_id)
        index = next((i for i, s in enumerate(siblings) if s.id == node_id), None)
        if index is None:
            return None
        target_index = index + direction
        if not (0 <= target_index < len(siblings)):
            return node
        siblings[index], siblings[target_index] = siblings[target_index], siblings[index]
        before_id = siblings[target_index - 1].id if target_index > 0 else None
        after_id = siblings[target_index + 1].id if target_index + 1 < len(siblings) else None
        return self.reorder_within_parent(node_id, before_id=before_id, after_id=after_id)

    def _sort_order_of(self, node_id: UUID | None) -> float | None:
        if node_id is None:
            return None
        node = self._repository.get_node(node_id)
        return node.sort_order if node is not None else None

    def archive_node(self, node_id: UUID) -> list[UUID]:
        subtree = self._repository.list_subtree(node_id, include_archived=False)
        affected_ids = [n.id for n in subtree]
        self._repository.set_archived(affected_ids, datetime.now(UTC))
        self._events.publish(NodeArchived(node_id=node_id, affected_ids=tuple(affected_ids)))
        return affected_ids

    def restore_node(self, node_id: UUID) -> list[UUID]:
        subtree = self._repository.list_subtree(node_id, include_archived=True)
        affected_ids = [n.id for n in subtree]
        self._repository.set_archived(affected_ids, None)
        self._events.publish(NodeRestored(node_id=node_id, affected_ids=tuple(affected_ids)))
        return affected_ids

    def duplicate_node(self, node_id: UUID) -> ManuscriptNode | None:
        """Shallow duplicate: the node itself (and, for text-bearing nodes, its
        content) but not its descendants - keeps the operation fast and
        predictable for the common "duplicate this scene" case."""
        node = self._repository.get_node(node_id)
        if node is None or node.parent_id is None:
            return None
        copy = self.create_node(node.parent_id, node.node_type, f"{node.title} Copy")
        if node.is_text_bearing:
            content = self._repository.get_document_content(node.id)
            self._repository.save_document_content(copy.id, content)
        return self._repository.get_node(copy.id)

    # --- word counts ---------------------------------------------------------------

    def list_subtree(self, node_id: UUID) -> list[ManuscriptNode]:
        return self._repository.list_subtree(node_id, include_archived=False)

    def subtree_word_count(self, node_id: UUID, *, respect_compile_flag: bool = False) -> int:
        subtree = self._repository.list_subtree(node_id, include_archived=False)
        return sum(
            n.word_count
            for n in subtree
            if n.is_text_bearing and (not respect_compile_flag or n.include_in_compile)
        )
