"""Metadata view for the currently selected asset, with editable tags."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from skrybe_studio.core.contracts.event import Event
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.assets.application.events import AssetSelectionChanged

if TYPE_CHECKING:
    from skrybe_studio.plugins.assets.plugin import AssetsPlugin

AUTOSAVE_DELAY_MS = 600


class AssetDetailsPanel(QWidget):
    def __init__(self, plugin: AssetsPlugin, events: EventBus) -> None:
        super().__init__()
        self._plugin = plugin
        self._current_asset_id: UUID | None = None
        self._loading = False

        self._filename_label = QLabel("—")
        self._mime_label = QLabel("—")
        self._size_label = QLabel("—")
        self._hash_label = QLabel("—")
        self._imported_label = QLabel("—")
        self._status_label = QLabel("—")
        self._status_label.setObjectName("warning")
        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("Tags, comma separated")
        self._tags_edit.textEdited.connect(self._schedule_save)

        form = QFormLayout()
        form.addRow("Filename", self._filename_label)
        form.addRow("Type", self._mime_label)
        form.addRow("Size", self._size_label)
        form.addRow("SHA-256", self._hash_label)
        form.addRow("Imported", self._imported_label)
        form.addRow("Status", self._status_label)
        form.addRow("Tags", self._tags_edit)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addStretch(1)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(AUTOSAVE_DELAY_MS)
        self._autosave_timer.timeout.connect(self._save_tags)

        events.subscribe(AssetSelectionChanged, self._on_selection_changed)
        self.setEnabled(False)

    def _on_selection_changed(self, event: Event) -> None:
        if isinstance(event, AssetSelectionChanged):
            self._load_asset(event.asset_id)

    def _load_asset(self, asset_id: UUID | None) -> None:
        self._save_tags()
        self._current_asset_id = asset_id
        service = self._plugin.service
        if asset_id is None or service is None:
            self.setEnabled(False)
            return
        asset = service.get_asset(asset_id)
        if asset is None:
            self.setEnabled(False)
            return
        self.setEnabled(True)
        self._loading = True
        self._filename_label.setText(asset.original_filename)
        self._mime_label.setText(asset.mime_type)
        self._size_label.setText(_format_size(asset.size_bytes))
        self._hash_label.setText(asset.content_hash)
        self._imported_label.setText(asset.imported_at.strftime("%Y-%m-%d %H:%M"))
        self._status_label.setText("Missing file" if service.is_missing(asset) else "OK")
        self._tags_edit.setText(", ".join(asset.tags))
        self._loading = False

    def _schedule_save(self) -> None:
        if self._loading:
            return
        self._autosave_timer.start()

    def _save_tags(self) -> None:
        self._autosave_timer.stop()
        if self._current_asset_id is None or self._plugin.service is None:
            return
        tags = tuple(t.strip() for t in self._tags_edit.text().split(",") if t.strip())
        self._plugin.service.set_tags(self._current_asset_id, tags)


def _format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    if size < 1024:
        return f"{int(size)} B"
    for unit in ("KB", "MB", "GB"):
        size /= 1024
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
    return f"{size:.1f} GB"
