"""Central registry of user- and system-triggered commands."""

from __future__ import annotations

import logging

from skrybe_studio.core.contracts.command import Command

logger = logging.getLogger(__name__)


class DuplicateCommandError(RuntimeError):
    """Raised when two commands are registered under the same stable ID."""


class CommandRegistry:
    """Registers commands and dispatches execution by stable command ID."""

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        if command.id in self._commands:
            raise DuplicateCommandError(f"Command '{command.id}' is already registered")
        self._commands[command.id] = command
        logger.debug("Registered command '%s'", command.id)

    def unregister(self, command_id: str) -> None:
        if self._commands.pop(command_id, None) is not None:
            logger.debug("Unregistered command '%s'", command_id)

    def get(self, command_id: str) -> Command | None:
        return self._commands.get(command_id)

    def all(self) -> list[Command]:
        return list(self._commands.values())

    def by_category(self) -> dict[str, list[Command]]:
        grouped: dict[str, list[Command]] = {}
        for command in self._commands.values():
            grouped.setdefault(command.category, []).append(command)
        return grouped

    def execute(self, command_id: str) -> None:
        command = self._commands.get(command_id)
        if command is None:
            raise KeyError(f"Unknown command '{command_id}'")
        if not command.is_enabled():
            logger.warning("Command '%s' is disabled; ignoring execute request", command_id)
            return
        logger.debug("Executing command '%s'", command_id)
        command.handler()
