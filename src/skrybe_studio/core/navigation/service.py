"""Cross-plugin Back/Forward history over entity IDs.

Deliberately Qt-free and side-effect-free - it only tracks a position in a
list of `NavigationTarget`s, exactly like the Manuscript plugin's own
(pre-existing, unchanged) `NavigationHistory` for its intra-document
Back/Forward. This is the same shape promoted to core so history can span
plugin boundaries: whoever calls `go_back()`/`go_forward()` is responsible
for taking the returned target and asking `EntityViewerRegistry.reveal()`
to actually show it - this class does not know Qt or workspaces exist.
"""

from __future__ import annotations

from skrybe_studio.core.contracts.navigation import NavigationTarget


class NavigationService:
    def __init__(self) -> None:
        self._history: list[NavigationTarget] = []
        self._index = -1

    def visit(self, target: NavigationTarget) -> None:
        """Records a visit, dropping any forward history - a no-op if
        `target` is already the current entry, matching Manuscript's own
        history semantics for the same reason: re-selecting what's already
        showing shouldn't create a redundant history entry.
        """
        if self._index >= 0 and self._history[self._index].entity_id == target.entity_id:
            return
        del self._history[self._index + 1 :]
        self._history.append(target)
        self._index += 1

    def clear(self) -> None:
        """Called when the open project changes - entity IDs from a closed
        project are meaningless once a different (or no) project is open.
        """
        self._history.clear()
        self._index = -1

    @property
    def can_go_back(self) -> bool:
        return self._index > 0

    @property
    def can_go_forward(self) -> bool:
        return self._index < len(self._history) - 1

    @property
    def current(self) -> NavigationTarget | None:
        return self._history[self._index] if self._index >= 0 else None

    def go_back(self) -> NavigationTarget | None:
        if not self.can_go_back:
            return None
        self._index -= 1
        return self.current

    def go_forward(self) -> NavigationTarget | None:
        if not self.can_go_forward:
            return None
        self._index += 1
        return self.current
