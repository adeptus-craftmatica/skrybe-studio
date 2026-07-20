"""Contextual metadata inspector: title, synopsis, status, label, compile
inclusion, tags, word targets/progress, and (for the manuscript root) an
optional cover image resolved through the shared `AssetLookup` capability.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from skrybe_studio.core.contracts.event import Event
from skrybe_studio.core.events.bus import EventBus
from skrybe_studio.plugins.manuscript.application.events import (
    DocumentContentChanged,
    NodeMetadataChanged,
    NodeRenamed,
    NodeSelectionChanged,
)
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType, NodeStatus

if TYPE_CHECKING:
    from skrybe_studio.plugins.manuscript.plugin import ManuscriptPlugin

logger = logging.getLogger(__name__)

_SUGGESTED_LABELS = ["", "Plot", "Character", "Research", "Needs Revision"]
_AUTOSAVE_DELAY_MS = 500


class InspectorPanel(QWidget):
    def __init__(self, plugin: ManuscriptPlugin, events: EventBus) -> None:
        super().__init__()
        self._plugin = plugin
        self._node_id: UUID | None = None
        self._loading = False

        self._title_edit = QLineEdit()
        self._title_edit.editingFinished.connect(self._on_title_edited)
        self._type_label = QLabel("—")
        self._created_label = QLabel("—")
        self._updated_label = QLabel("—")
        self._word_count_label = QLabel("—")

        self._status_combo = QComboBox()
        for status in NodeStatus:
            self._status_combo.addItem(status.value.title(), status)
        self._status_combo.currentIndexChanged.connect(self._schedule_metadata_save)

        self._label_combo = QComboBox()
        self._label_combo.setEditable(True)
        self._label_combo.addItems(_SUGGESTED_LABELS)
        self._label_combo.currentTextChanged.connect(self._schedule_metadata_save)

        self._compile_checkbox = QCheckBox("Include in compile")
        self._compile_checkbox.toggled.connect(self._schedule_metadata_save)

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("Tags, comma separated")
        self._tags_edit.editingFinished.connect(self._schedule_metadata_save)

        self._target_spin = QSpinBox()
        self._target_spin.setRange(0, 1_000_000)
        self._target_spin.setSpecialValueText("No target")
        self._target_spin.valueChanged.connect(self._schedule_target_save)
        self._progress_label = QLabel("—")

        self._synopsis_edit = QPlainTextEdit()
        self._synopsis_edit.setPlaceholderText("Synopsis…")
        self._synopsis_edit.setMaximumHeight(96)
        self._synopsis_edit.textChanged.connect(self._schedule_metadata_save)

        self._cover_label = QLabel("No cover image")
        self._cover_label.setObjectName("muted")
        self._cover_thumbnail = QLabel()
        self._cover_button = QPushButton("Choose Cover…")
        self._cover_button.clicked.connect(self._on_choose_cover)
        self._clear_cover_button = QPushButton("Clear Cover")
        self._clear_cover_button.clicked.connect(self._on_clear_cover)

        form = QFormLayout()
        form.addRow("Title", self._title_edit)
        form.addRow("Type", self._type_label)
        form.addRow("Status", self._status_combo)
        form.addRow("Label", self._label_combo)
        form.addRow("", self._compile_checkbox)
        form.addRow("Tags", self._tags_edit)
        form.addRow("Target words", self._target_spin)
        form.addRow("Progress", self._progress_label)
        form.addRow("Word count", self._word_count_label)
        form.addRow("Created", self._created_label)
        form.addRow("Updated", self._updated_label)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel("Synopsis"))
        layout.addWidget(self._synopsis_edit)
        layout.addWidget(self._cover_label)
        layout.addWidget(self._cover_thumbnail)
        layout.addWidget(self._cover_button)
        layout.addWidget(self._clear_cover_button)
        layout.addStretch(1)

        self._metadata_timer = QTimer(self)
        self._metadata_timer.setSingleShot(True)
        self._metadata_timer.setInterval(_AUTOSAVE_DELAY_MS)
        self._metadata_timer.timeout.connect(self._save_metadata)

        self._target_timer = QTimer(self)
        self._target_timer.setSingleShot(True)
        self._target_timer.setInterval(_AUTOSAVE_DELAY_MS)
        self._target_timer.timeout.connect(self._save_target)

        events.subscribe(NodeSelectionChanged, self._on_selection_changed)
        events.subscribe(DocumentContentChanged, self._on_content_changed)
        events.subscribe(NodeMetadataChanged, self._on_metadata_changed_externally)
        events.subscribe(NodeRenamed, self._on_metadata_changed_externally)

        self.setEnabled(False)

    # --- loading -------------------------------------------------------------------

    def _on_selection_changed(self, event: Event) -> None:
        if isinstance(event, NodeSelectionChanged):
            self._load_node(event.node_id)

    def _on_content_changed(self, event: Event) -> None:
        if isinstance(event, DocumentContentChanged) and event.node_id == self._node_id:
            self._update_word_count_display()
            self._update_progress_display()

    def _on_metadata_changed_externally(self, event: Event) -> None:
        node_id = getattr(event, "node_id", None)
        if node_id == self._node_id and self._node_id is not None and not self._loading:
            self._load_node(self._node_id)

    def _load_node(self, node_id: UUID | None) -> None:
        self._flush_pending()
        self._node_id = node_id
        if node_id is None or self._plugin.hierarchy is None:
            self.setEnabled(False)
            return
        node = self._plugin.hierarchy.get_node(node_id)
        if node is None:
            self.setEnabled(False)
            return
        self.setEnabled(True)
        self._loading = True
        self._title_edit.setText(node.title)
        self._type_label.setText(node.node_type.value.title())
        status_index = self._status_combo.findData(node.status)
        if status_index >= 0:
            self._status_combo.setCurrentIndex(status_index)
        self._label_combo.setCurrentText(node.label)
        self._compile_checkbox.setChecked(node.include_in_compile)
        self._tags_edit.setText(", ".join(node.tags))
        self._synopsis_edit.setPlainText(node.synopsis)
        self._target_spin.setValue(node.target_word_count or 0)
        self._created_label.setText(node.created_at.strftime("%Y-%m-%d %H:%M"))
        self._updated_label.setText(node.updated_at.strftime("%Y-%m-%d %H:%M"))
        self._update_word_count_display()
        self._update_progress_display()

        is_manuscript_root = node.node_type == ManuscriptNodeType.MANUSCRIPT
        for widget in (
            self._cover_label,
            self._cover_thumbnail,
            self._cover_button,
            self._clear_cover_button,
        ):
            widget.setVisible(is_manuscript_root)
        if is_manuscript_root:
            self._update_cover_display()
        self._loading = False

    def _update_word_count_display(self) -> None:
        if self._node_id is None or self._plugin.hierarchy is None:
            return
        node = self._plugin.hierarchy.get_node(self._node_id)
        if node is None:
            return
        if node.is_text_bearing:
            self._word_count_label.setText(str(node.word_count))
        else:
            total = self._plugin.hierarchy.subtree_word_count(self._node_id)
            self._word_count_label.setText(f"{total} (subtree)")

    def _update_progress_display(self) -> None:
        if self._node_id is None or self._plugin.hierarchy is None:
            return
        node = self._plugin.hierarchy.get_node(self._node_id)
        if node is None or not node.target_word_count:
            self._progress_label.setText("—")
            return
        current = (
            node.word_count
            if node.is_text_bearing
            else self._plugin.hierarchy.subtree_word_count(self._node_id)
        )
        self._progress_label.setText(f"{current} / {node.target_word_count}")

    # --- saving ------------------------------------------------------------------------

    def _on_title_edited(self) -> None:
        if self._loading or self._node_id is None or self._plugin.hierarchy is None:
            return
        title = self._title_edit.text().strip()
        if title:
            self._plugin.hierarchy.rename_node(self._node_id, title)

    def _schedule_metadata_save(self, *_args: object) -> None:
        if not self._loading:
            self._metadata_timer.start()

    def _save_metadata(self) -> None:
        self._metadata_timer.stop()
        if self._node_id is None or self._plugin.hierarchy is None:
            return
        tags = tuple(t.strip() for t in self._tags_edit.text().split(",") if t.strip())
        self._plugin.hierarchy.update_metadata(
            self._node_id,
            synopsis=self._synopsis_edit.toPlainText(),
            status=self._status_combo.currentData(),
            label=self._label_combo.currentText().strip(),
            include_in_compile=self._compile_checkbox.isChecked(),
            tags=tags,
        )

    def _schedule_target_save(self, _value: int) -> None:
        if not self._loading:
            self._target_timer.start()

    def _save_target(self) -> None:
        self._target_timer.stop()
        if self._node_id is None or self._plugin.hierarchy is None:
            return
        self._plugin.hierarchy.set_target_word_count(
            self._node_id, self._target_spin.value() or None
        )
        self._update_progress_display()

    def _flush_pending(self) -> None:
        if self._metadata_timer.isActive():
            self._save_metadata()
        if self._target_timer.isActive():
            self._save_target()

    # --- cover asset (graceful when the Asset Library plugin is unavailable) -----------

    def _update_cover_display(self) -> None:
        if self._node_id is None or self._plugin.assets is None:
            return
        if not self._plugin.assets.is_asset_library_available:
            self._cover_label.setText("Asset Library unavailable")
            self._cover_thumbnail.clear()
            self._cover_button.setEnabled(False)
            self._clear_cover_button.setEnabled(False)
            return
        self._cover_button.setEnabled(True)
        self._clear_cover_button.setEnabled(True)
        title = self._plugin.assets.cover_asset_title(self._node_id)
        self._cover_label.setText(title or "No cover image")
        thumbnail_path = self._plugin.assets.resolve_cover_thumbnail(self._node_id)
        if thumbnail_path is not None and thumbnail_path.exists():
            pixmap = QPixmap(str(thumbnail_path))
            if not pixmap.isNull():
                self._cover_thumbnail.setPixmap(pixmap.scaledToWidth(120))
                return
        self._cover_thumbnail.clear()

    def _on_choose_cover(self) -> None:
        if self._node_id is None or self._plugin.assets is None:
            return
        available = self._plugin.assets.list_available_assets()
        if not available:
            self._cover_label.setText("No assets available to choose from")
            return
        menu = QMenu(self)
        for asset_id, title in available:
            action = menu.addAction(title)
            action.triggered.connect(lambda _checked, a=asset_id: self._set_cover(a))
        menu.exec(self._cover_button.mapToGlobal(self._cover_button.rect().bottomLeft()))

    def _set_cover(self, asset_id: UUID) -> None:
        if self._node_id is not None and self._plugin.assets is not None:
            self._plugin.assets.set_cover_asset(self._node_id, asset_id)
            self._update_cover_display()

    def _on_clear_cover(self) -> None:
        if self._node_id is not None and self._plugin.assets is not None:
            self._plugin.assets.clear_cover_asset(self._node_id)
            self._update_cover_display()
