"""Undo/redo stack. Wraps Qt's `QUndoStack` behind the plain `UndoableCommand` contract."""

from __future__ import annotations

from PySide6.QtGui import QUndoCommand, QUndoStack

from skrybe_studio.core.undo.contracts import UndoableCommand


class _CommandAdapter(QUndoCommand):
    """Bridges a plain `UndoableCommand` into Qt's `QUndoCommand` shape."""

    def __init__(self, command: UndoableCommand) -> None:
        super().__init__(command.description)
        self._command = command

    def redo(self) -> None:
        self._command.do()

    def undo(self) -> None:
        self._command.undo()


class UndoService:
    """Domain-facing undo/redo stack. Push an `UndoableCommand`; Qt is an
    implementation detail hidden behind this narrow interface."""

    def __init__(self) -> None:
        self._stack = QUndoStack()

    def push(self, command: UndoableCommand) -> None:
        self._stack.push(_CommandAdapter(command))

    def undo(self) -> None:
        self._stack.undo()

    def redo(self) -> None:
        self._stack.redo()

    def clear(self) -> None:
        self._stack.clear()

    @property
    def can_undo(self) -> bool:
        return self._stack.canUndo()

    @property
    def can_redo(self) -> bool:
        return self._stack.canRedo()

    @property
    def undo_text(self) -> str:
        return self._stack.undoText()

    @property
    def redo_text(self) -> str:
        return self._stack.redoText()

    def qt_stack(self) -> QUndoStack:
        """Escape hatch for wiring QAction-based undo/redo menu items to Qt directly."""
        return self._stack
