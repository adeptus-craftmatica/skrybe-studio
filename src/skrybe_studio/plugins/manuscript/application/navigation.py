"""Back/forward navigation history over manuscript node IDs.

Operates purely on IDs, never UI object references, so it stays valid
across binder rebuilds and is trivially testable without Qt.
"""

from __future__ import annotations

from uuid import UUID


class NavigationHistory:
    def __init__(self, *, max_length: int = 100) -> None:
        self._back: list[UUID] = []
        self._forward: list[UUID] = []
        self._current: UUID | None = None
        self._max_length = max_length

    @property
    def current(self) -> UUID | None:
        return self._current

    def visit(self, node_id: UUID) -> None:
        """Records a navigation to `node_id` as a new history entry."""
        if node_id == self._current:
            return
        if self._current is not None:
            self._back.append(self._current)
            if len(self._back) > self._max_length:
                self._back.pop(0)
        self._forward.clear()
        self._current = node_id

    @property
    def can_go_back(self) -> bool:
        return bool(self._back)

    @property
    def can_go_forward(self) -> bool:
        return bool(self._forward)

    def go_back(self) -> UUID | None:
        if not self._back:
            return None
        if self._current is not None:
            self._forward.append(self._current)
        self._current = self._back.pop()
        return self._current

    def go_forward(self) -> UUID | None:
        if not self._forward:
            return None
        if self._current is not None:
            self._back.append(self._current)
        self._current = self._forward.pop()
        return self._current
