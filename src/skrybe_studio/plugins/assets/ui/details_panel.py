"""Metadata view for the currently selected asset: full preview, editable tags, and backlinks."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from skrybe_studio.core.contracts.event import Event
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.assets.application.events import AssetSelectionChanged

if TYPE_CHECKING:
    from skrybe_studio.plugins.assets.plugin import AssetsPlugin

AUTOSAVE_DELAY_MS = 600
PREVIEW_MIN_HEIGHT = 160
PREVIEW_MAX_HEIGHT = 420


class AssetDetailsPanel(QWidget):
    def __init__(self, plugin: AssetsPlugin, events: EventBus) -> None:
        super().__init__()
        self._plugin = plugin
        self._current_asset_id: UUID | None = None
        self._loading = False
        self._original_pixmap: QPixmap | None = None

        self._preview_label = QLabel("No preview available")
        self._preview_label.setObjectName("muted")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumHeight(PREVIEW_MIN_HEIGHT)
        self._preview_label.setMaximumHeight(PREVIEW_MAX_HEIGHT)

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

        self._links_label = QLabel("Linked From")
        self._links_label.setObjectName("muted")
        self._links_list = QListWidget()
        self._links_list.setMaximumHeight(120)

        layout = QVBoxLayout(self)
        layout.addWidget(self._preview_label)
        layout.addLayout(form)
        layout.addWidget(self._links_label)
        layout.addWidget(self._links_list)
        layout.addStretch(1)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(AUTOSAVE_DELAY_MS)
        self._autosave_timer.timeout.connect(self._save_tags)

        events.subscribe(AssetSelectionChanged, self._on_selection_changed)
        self.setEnabled(False)
        self._clear_links()

    def _on_selection_changed(self, event: Event) -> None:
        if isinstance(event, AssetSelectionChanged):
            self._load_asset(event.asset_id)

    def _load_asset(self, asset_id: UUID | None) -> None:
        self._save_tags()
        self._current_asset_id = asset_id
        service = self._plugin.service
        if asset_id is None or service is None:
            self.setEnabled(False)
            self._set_preview(None)
            self._clear_links()
            return
        asset = service.get_asset(asset_id)
        if asset is None:
            self.setEnabled(False)
            self._set_preview(None)
            self._clear_links()
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

        if asset.mime_type.startswith("image/") and not service.is_missing(asset):
            self._set_preview(QPixmap(str(service.resolve_path(asset))))
        else:
            self._set_preview(None)

        self._refresh_links(asset_id)

    def _set_preview(self, pixmap: QPixmap | None) -> None:
        self._original_pixmap = pixmap if pixmap is not None and not pixmap.isNull() else None
        self._render_preview()

    def _render_preview(self) -> None:
        if self._original_pixmap is None:
            self._preview_label.setText("No preview available")
            self._preview_label.setPixmap(QPixmap())
            return
        target_height = min(self._preview_label.height(), PREVIEW_MAX_HEIGHT)
        scaled = self._original_pixmap.scaled(
            self._preview_label.width() or self._original_pixmap.width(),
            target_height or self._original_pixmap.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_label.setPixmap(scaled)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._render_preview()

    def _clear_links(self) -> None:
        self._links_list.clear()
        self._links_label.setVisible(False)
        self._links_list.setVisible(False)

    def _refresh_links(self, asset_id: UUID) -> None:
        self._links_list.clear()
        entities = self._plugin.entities
        relationships = self._plugin.relationships
        if entities is None or relationships is None:
            self._clear_links()
            return
        for relationship in relationships.for_entity(asset_id):
            if relationship.target_entity_id != asset_id:
                continue
            source = entities.get(relationship.source_entity_id)
            if source is None:
                continue
            label = (
                f"{source.title}  —  {_humanize_relationship_type(relationship.relationship_type)}"
            )
            self._links_list.addItem(QListWidgetItem(label))
        has_links = self._links_list.count() > 0
        self._links_label.setVisible(has_links)
        self._links_list.setVisible(has_links)

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


def _humanize_relationship_type(relationship_type: str) -> str:
    """Turn e.g. "manuscript.cover_asset" into "Cover Asset" without knowing what a
    manuscript is - Assets must not import another plugin's relationship-type
    constants, so this only ever looks at the generic string shape.
    """
    label = relationship_type.rsplit(".", 1)[-1]
    return label.replace("_", " ").replace("-", " ").title()


def _format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    if size < 1024:
        return f"{int(size)} B"
    for unit in ("KB", "MB", "GB"):
        size /= 1024
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
    return f"{size:.1f} GB"
