"""Loads and saves text-bearing document content, tracking daily word-count deltas."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.manuscript.application.events import DocumentContentChanged
from skrybe_studio.plugins.manuscript.domain.document_ir import DocumentContent
from skrybe_studio.plugins.manuscript.infrastructure.repositories import (
    ManuscriptRepository,
    ProgressRepository,
)

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self, repository: ManuscriptRepository, progress: ProgressRepository, events: EventBus
    ) -> None:
        self._repository = repository
        self._progress = progress
        self._events = events

    def load_content(self, node_id: UUID) -> DocumentContent:
        return self._repository.get_document_content(node_id)

    def save_content(self, node_id: UUID, content: DocumentContent) -> int:
        node = self._repository.get_node(node_id)
        if node is None:
            raise ValueError(f"Unknown manuscript node {node_id}")
        previous_word_count = node.word_count
        new_word_count = self._repository.save_document_content(node_id, content)
        delta = new_word_count - previous_word_count
        if delta != 0:
            self._progress.record_delta(node.manuscript_id, datetime.now(UTC).date(), delta)
        logger.debug("Saved content for node %s (%d words)", node_id, new_word_count)
        self._events.publish(DocumentContentChanged(node_id=node_id, word_count=new_word_count))
        return new_word_count
