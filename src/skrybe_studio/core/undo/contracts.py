"""The domain-facing undoable-command contract.

Plugins implement this plain protocol - no Qt import required - and push
instances onto `UndoService`. See `docs/plugin-development.md` for the
pattern plugins should follow to contribute undoable actions.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class UndoableCommand(Protocol):
    description: str

    def do(self) -> None: ...

    def undo(self) -> None: ...
