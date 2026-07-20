from __future__ import annotations

import pytest

from skrybe_studio.core.commands.registry import CommandRegistry, DuplicateCommandError
from skrybe_studio.core.contracts.command import Command


def _command(command_id: str = "app.test", *, enabled: bool = True, handler=None) -> Command:
    calls: list[str] = []

    def default_handler() -> None:
        calls.append(command_id)

    return Command(
        id=command_id,
        title="Test Command",
        handler=handler or default_handler,
        is_enabled=lambda: enabled,
    )


def test_register_and_get() -> None:
    registry = CommandRegistry()
    command = _command()
    registry.register(command)

    assert registry.get("app.test") is command
    assert registry.all() == [command]


def test_duplicate_registration_raises() -> None:
    registry = CommandRegistry()
    registry.register(_command())

    with pytest.raises(DuplicateCommandError):
        registry.register(_command())


def test_execute_invokes_handler() -> None:
    registry = CommandRegistry()
    calls: list[str] = []
    registry.register(_command(handler=lambda: calls.append("ran")))

    registry.execute("app.test")

    assert calls == ["ran"]


def test_execute_disabled_command_does_not_invoke_handler() -> None:
    registry = CommandRegistry()
    calls: list[str] = []
    registry.register(_command(enabled=False, handler=lambda: calls.append("ran")))

    registry.execute("app.test")

    assert calls == []


def test_execute_unknown_command_raises_key_error() -> None:
    registry = CommandRegistry()
    with pytest.raises(KeyError):
        registry.execute("does.not.exist")


def test_by_category_groups_commands() -> None:
    registry = CommandRegistry()
    registry.register(Command(id="a", title="A", handler=lambda: None, category="Notes"))
    registry.register(Command(id="b", title="B", handler=lambda: None, category="Notes"))
    registry.register(Command(id="c", title="C", handler=lambda: None, category="Assets"))

    grouped = registry.by_category()

    assert {c.id for c in grouped["Notes"]} == {"a", "b"}
    assert {c.id for c in grouped["Assets"]} == {"c"}
