"""A command palette: fuzzy filter over every registered command."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from skrybe_studio.core.commands.fuzzy import fuzzy_match
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
        needle = text.strip()

        scored: list[tuple[float, str, str]] = []
        for command in self._commands.all():
            title_match = fuzzy_match(needle, command.title)
            id_match = fuzzy_match(needle, command.id)
            if not (title_match.matched or id_match.matched):
                continue
            best_score = max(title_match.score, id_match.score)
            scored.append((best_score, command.id, f"{command.title}   ({command.category})"))

        scored.sort(key=lambda entry: entry[0], reverse=True)
        for _score, command_id, label in scored:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, command_id)
            self._list.addItem(item)

    def _execute_item(self, item: QListWidgetItem) -> None:
        command_id = item.data(Qt.ItemDataRole.UserRole)
        self._commands.execute(command_id)
        self.accept()

    def _execute_first(self) -> None:
        item = self._list.item(0)
        if item is not None:
            self._execute_item(item)
