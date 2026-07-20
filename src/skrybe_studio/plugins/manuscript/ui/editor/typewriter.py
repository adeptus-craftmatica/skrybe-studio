"""Pure positioning math for typewriter scrolling.

Kept separate from any Qt widget so the calculation itself is testable
without a real GUI event loop - only the thin call site in
`document_editor.py` touches actual widget geometry.
"""

from __future__ import annotations

DEFAULT_POSITION_RATIO = 0.4


def target_scroll_value(
    current_scroll: int,
    cursor_top: int,
    viewport_height: int,
    *,
    position_ratio: float = DEFAULT_POSITION_RATIO,
) -> int:
    """The new vertical scrollbar value that brings the cursor to `position_ratio`
    down the viewport, given its current pixel offset within that viewport."""
    target_y = int(viewport_height * position_ratio)
    return current_scroll + (cursor_top - target_y)
