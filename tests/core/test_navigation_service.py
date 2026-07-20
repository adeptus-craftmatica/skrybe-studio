from __future__ import annotations

from uuid import uuid4

from skrybe_studio.core.contracts.navigation import NavigationTarget
from skrybe_studio.core.navigation.service import NavigationService


def _target(entity_type: str = "story_bible.character") -> NavigationTarget:
    return NavigationTarget(entity_id=uuid4(), entity_type=entity_type)


def test_fresh_service_has_no_history() -> None:
    service = NavigationService()

    assert service.current is None
    assert service.can_go_back is False
    assert service.can_go_forward is False


def test_visit_becomes_current() -> None:
    service = NavigationService()
    target = _target()

    service.visit(target)

    assert service.current == target


def test_go_back_returns_the_previous_target() -> None:
    service = NavigationService()
    first, second = _target(), _target()
    service.visit(first)
    service.visit(second)

    result = service.go_back()

    assert result == first
    assert service.current == first


def test_go_forward_returns_to_the_later_target() -> None:
    service = NavigationService()
    first, second = _target(), _target()
    service.visit(first)
    service.visit(second)
    service.go_back()

    result = service.go_forward()

    assert result == second


def test_visiting_a_new_target_drops_forward_history() -> None:
    service = NavigationService()
    first, second, third = _target(), _target(), _target()
    service.visit(first)
    service.visit(second)
    service.go_back()

    service.visit(third)

    assert service.can_go_forward is False
    assert service.current == third


def test_revisiting_the_current_target_is_a_no_op() -> None:
    service = NavigationService()
    target = _target()
    service.visit(target)
    service.visit(target)  # same entity_id again

    service.go_back()

    assert service.can_go_back is False  # only one real entry was ever recorded


def test_go_back_at_the_start_returns_none() -> None:
    service = NavigationService()
    service.visit(_target())

    assert service.go_back() is None


def test_go_forward_at_the_end_returns_none() -> None:
    service = NavigationService()
    service.visit(_target())

    assert service.go_forward() is None


def test_clear_resets_history() -> None:
    service = NavigationService()
    service.visit(_target())
    service.visit(_target())

    service.clear()

    assert service.current is None
    assert service.can_go_back is False
    assert service.can_go_forward is False
