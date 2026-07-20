"""A minimal command palette: substring filter over every registered command."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from skrybe_studio.core.commands.registry import CommandRegistry


class CommandPalette(QDialog):
    def __init__(self, commands: CommandRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setMinimumWidth(420)
        self._commands = commands

        self._search = QLineEdit()
        self._search.setPlaceholderText("Type a command…")
        self._list = QListWidget()

        layout = QVBoxLayout(self)
        layout.addWidget(self._search)
        layout.addWidget(self._list)

        self._search.textChanged.connect(self._refresh)
        self._search.returnPressed.connect(self._execute_first)
        self._list.itemActivated.connect(self._execute_item)

        self._refresh("")
        self._search.setFocus()

    def _refresh(self, text: str) -> None:
        self._list.clear()
        needle = text.strip().lower()
        for command in self._commands.all():
            if needle in command.title.lower() or needle in command.id.lower():
                item = QListWidgetItem(f"{command.title}   ({command.category})")
                item.setData(Qt.ItemDataRole.UserRole, command.id)
                self._list.addItem(item)

    def _execute_item(self, item: QListWidgetItem) -> None:
        command_id = item.data(Qt.ItemDataRole.UserRole)
        self._commands.execute(command_id)
        self.accept()

    def _execute_first(self) -> None:
        item = self._list.item(0)
        if item is not None:
            self._execute_item(item)
