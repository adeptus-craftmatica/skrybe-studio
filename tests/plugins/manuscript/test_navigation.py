from __future__ import annotations

from uuid import uuid4

from skrybe_studio.plugins.manuscript.application.navigation import NavigationHistory


def test_visit_sets_current_and_does_not_affect_back_stack_on_first_visit() -> None:
    history = NavigationHistory()
    node_id = uuid4()

    history.visit(node_id)

    assert history.current == node_id
    assert history.can_go_back is False


def test_back_and_forward_between_two_visits() -> None:
    history = NavigationHistory()
    first, second = uuid4(), uuid4()
    history.visit(first)
    history.visit(second)

    assert history.can_go_back is True
    assert history.go_back() == first
    assert history.can_go_forward is True
    assert history.go_forward() == second


def test_visiting_after_going_back_clears_forward_stack() -> None:
    history = NavigationHistory()
    first, second, third = uuid4(), uuid4(), uuid4()
    history.visit(first)
    history.visit(second)
    history.go_back()

    history.visit(third)

    assert history.can_go_forward is False


def test_visiting_the_same_node_again_is_a_no_op() -> None:
    history = NavigationHistory()
    node_id = uuid4()
    history.visit(node_id)
    history.visit(node_id)

    assert history.can_go_back is False


def test_go_back_with_empty_history_returns_none() -> None:
    history = NavigationHistory()
    assert history.go_back() is None
    assert history.go_forward() is None
