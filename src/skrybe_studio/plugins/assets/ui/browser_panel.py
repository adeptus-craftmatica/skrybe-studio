"""Grid browser for imported assets: import, search, remove, and reveal on disk."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from skrybe_studio.core.contracts.event import Event
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.assets.application.events import (
    AssetImported,
    AssetMetadataChanged,
    AssetRemoved,
    AssetSelectionChanged,
)

if TYPE_CHECKING:
    from skrybe_studio.plugins.assets.plugin import AssetsPlugin

IMPORT_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.svg);;Text files (*.txt);;All files (*.*)"


class AssetsBrowserPanel(QWidget):
    def __init__(self, plugin: AssetsPlugin, events: EventBus) -> None:
        super().__init__()
        self._plugin = plugin
        self._events = events

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search assets…")
        self._search.textChanged.connect(self._refresh)

        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setIconSize(QSize(96, 96))
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setSpacing(8)
        self._list.currentItemChanged.connect(self._on_selection_changed)

        import_button = QPushButton("Import Asset…")
        import_button.setObjectName("primary")
        import_button.clicked.connect(self._on_import)
        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(self._on_remove)
        reveal_button = QPushButton("Reveal in Folder")
        reveal_button.clicked.connect(self._on_reveal)

        button_row = QHBoxLayout()
        button_row.addWidget(import_button)
        button_row.addWidget(remove_button)
        button_row.addWidget(reveal_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._search)
        layout.addWidget(self._list)
        layout.addLayout(button_row)

        events.subscribe(AssetImported, self._on_asset_changed)
        events.subscribe(AssetMetadataChanged, self._on_asset_changed)
        events.subscribe(AssetRemoved, self._on_asset_changed)

        self._refresh("")

    def _on_asset_changed(self, _event: Event) -> None:
        self._refresh(self._search.text())

    def _refresh(self, query: str) -> None:
        self._list.clear()
        service = self._plugin.service
        if service is None:
            return
        assets = service.search_assets(query) if query.strip() else service.list_assets()
        for asset in assets:
            label = asset.original_filename
            if service.is_missing(asset):
                label += "  (missing)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, asset.id)
            thumbnail_path = service.thumbnail_path(asset.id)
            if thumbnail_path is not None:
                pixmap = QPixmap(str(thumbnail_path))
                if not pixmap.isNull():
                    item.setIcon(QIcon(pixmap))
            self._list.addItem(item)

    def _on_selection_changed(self) -> None:
        item = self._list.currentItem()
        asset_id: UUID | None = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        self._plugin.set_selected_asset(asset_id)
        self._events.publish(AssetSelectionChanged(asset_id=asset_id))

    def _on_import(self) -> None:
        if self._plugin.service is None:
            return
        paths, _selected_filter = QFileDialog.getOpenFileNames(
            self, "Import Asset", "", IMPORT_FILTER
        )
        for path in paths:
            self._plugin.service.import_asset(
                Path(path), on_imported=lambda _asset_id: self._refresh(self._search.text())
            )

    def _on_remove(self) -> None:
        item = self._list.currentItem()
        if item is None or self._plugin.service is None:
            return
        self._plugin.service.remove_asset(item.data(Qt.ItemDataRole.UserRole))

    def _on_reveal(self) -> None:
        item = self._list.currentItem()
        if item is None or self._plugin.service is None:
            return
        asset = self._plugin.service.get_asset(item.data(Qt.ItemDataRole.UserRole))
        if asset is None:
            return
        path = self._plugin.service.resolve_path(asset)
        if not path.exists():
            QMessageBox.warning(
                self, "Reveal Asset", f"The file for '{asset.original_filename}' is missing."
            )
            return
        _reveal_in_file_manager(path)


def _reveal_in_file_manager(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", str(path)], check=False)
    elif sys.platform.startswith("win"):
        subprocess.run(["explorer", "/select,", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path.parent)], check=False)
