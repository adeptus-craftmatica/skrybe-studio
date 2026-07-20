"""Snapshots dialog: create, preview, compare, restore, and delete document snapshots."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from skrybe_studio.plugins.manuscript.application.diff import DiffLineKind

if TYPE_CHECKING:
    from skrybe_studio.plugins.manuscript.plugin import ManuscriptPlugin

_DIFF_PREFIX = {
    DiffLineKind.EQUAL: "  ",
    DiffLineKind.INSERT: "+ ",
    DiffLineKind.DELETE: "- ",
}


class SnapshotsDialog(QDialog):
    def __init__(
        self, plugin: ManuscriptPlugin, node_id: UUID, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._plugin = plugin
        self._node_id = node_id
        self.setWindowTitle("Snapshots")
        self.setMinimumSize(560, 420)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_selection_changed)
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)

        splitter = QSplitter()
        splitter.addWidget(self._list)
        splitter.addWidget(self._preview)
        splitter.setStretchFactor(1, 1)

        create_button = QPushButton("Create Snapshot")
        create_button.setObjectName("primary")
        create_button.clicked.connect(self._on_create)
        compare_button = QPushButton("Compare to Current")
        compare_button.clicked.connect(self._on_compare)
        restore_button = QPushButton("Restore")
        restore_button.clicked.connect(self._on_restore)
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self._on_delete)

        button_row = QHBoxLayout()
        for button in (create_button, compare_button, restore_button, delete_button):
            button_row.addWidget(button)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter, stretch=1)
        layout.addLayout(button_row)

        self._refresh()

    def _refresh(self) -> None:
        self._list.clear()
        self._preview.clear()
        if self._plugin.snapshots is None:
            return
        for snapshot in self._plugin.snapshots.list_snapshots(self._node_id):
            label = snapshot.name or snapshot.created_at.strftime("%Y-%m-%d %H:%M")
            item = QListWidgetItem(f"{label}   ({snapshot.word_count} words)")
            item.setData(Qt.ItemDataRole.UserRole, snapshot.id)
            self._list.addItem(item)

    def _current_snapshot_id(self) -> UUID | None:
        item = self._list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _on_selection_changed(self, _row: int) -> None:
        snapshot_id = self._current_snapshot_id()
        if snapshot_id is None or self._plugin.snapshots is None:
            self._preview.clear()
            return
        snapshot = self._plugin.snapshots.get_snapshot(snapshot_id)
        self._preview.setPlainText(snapshot.plain_text if snapshot is not None else "")

    def _on_create(self) -> None:
        if self._plugin.snapshots is None:
            return
        name, accepted = QInputDialog.getText(self, "Create Snapshot", "Name (optional):")
        if accepted:
            self._plugin.snapshots.create_snapshot(self._node_id, name=name.strip())
            self._refresh()

    def _on_compare(self) -> None:
        snapshot_id = self._current_snapshot_id()
        if snapshot_id is None or self._plugin.snapshots is None:
            return
        diff = self._plugin.snapshots.diff_against_current(snapshot_id)
        if diff is None:
            return
        lines = [f"{_DIFF_PREFIX[line.kind]}{line.text}" for line in diff]
        self._preview.setPlainText("\n".join(lines))

    def _on_restore(self) -> None:
        snapshot_id = self._current_snapshot_id()
        if snapshot_id is None or self._plugin.snapshots is None:
            return
        answer = QMessageBox.question(
            self,
            "Restore Snapshot",
            "Restore this snapshot? A safety snapshot of the current content is created first.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._plugin.snapshots.restore_snapshot(snapshot_id)
            self._refresh()

    def _on_delete(self) -> None:
        snapshot_id = self._current_snapshot_id()
        if snapshot_id is None or self._plugin.snapshots is None:
            return
        answer = QMessageBox.question(
            self,
            "Delete Snapshot",
            "Delete this snapshot? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._plugin.snapshots.delete_snapshot(snapshot_id)
            self._refresh()
