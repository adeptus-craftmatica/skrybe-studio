"""Pure positioning math for typewriter scrolling - no Qt widget required."""

from __future__ import annotations

from skrybe_studio.plugins.manuscript.ui.editor.typewriter import target_scroll_value


def test_cursor_above_target_position_scrolls_up() -> None:
    # Cursor at pixel 50, target position is 40% of a 200px viewport = 80.
    new_value = target_scroll_value(current_scroll=100, cursor_top=50, viewport_height=200)

    assert new_value == 100 + (50 - 80)


def test_cursor_at_target_position_does_not_move() -> None:
    new_value = target_scroll_value(current_scroll=100, cursor_top=80, viewport_height=200)

    assert new_value == 100


def test_custom_position_ratio_is_respected() -> None:
    new_value = target_scroll_value(
        current_scroll=0, cursor_top=100, viewport_height=200, position_ratio=0.5
    )

    assert new_value == 0 + (100 - 100)
