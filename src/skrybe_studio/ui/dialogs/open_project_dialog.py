"""Open Project dialog: pick from recent projects or browse for a directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class OpenProjectDialog(QDialog):
    def __init__(
        self, recent_projects: list[dict[str, Any]], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Open Project")
        self.setMinimumSize(480, 360)
        self._browsed_path: Path | None = None

        heading = QLabel("Recent Projects")
        heading.setObjectName("heading")

        self._list = QListWidget()
        for entry in recent_projects:
            item = QListWidgetItem(f"{entry.get('name', '?')}  —  {entry.get('path', '')}")
            item.setData(Qt.ItemDataRole.UserRole, entry.get("path"))
            self._list.addItem(item)
        self._list.itemDoubleClicked.connect(lambda _item: self.accept())

        browse_button = QPushButton("Browse for Project…")
        browse_button.clicked.connect(self._browse)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(heading)
        layout.addWidget(self._list)
        layout.addWidget(browse_button)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose Project Directory")
        if directory:
            self._browsed_path = Path(directory)
            self.accept()

    def selected_path(self) -> Path | None:
        if self._browsed_path is not None:
            return self._browsed_path
        item = self._list.currentItem()
        if item is None:
            return None
        raw = item.data(Qt.ItemDataRole.UserRole)
        return Path(raw) if raw else None
