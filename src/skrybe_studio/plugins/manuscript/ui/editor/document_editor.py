"""A single text-bearing node's editor: formatting toolbar, find/replace,
debounced autosave with an explicit flush, and live word counts.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QFont, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from skrybe_studio.plugins.manuscript.domain.document_ir import BlockKind
from skrybe_studio.plugins.manuscript.domain.word_count import count_words
from skrybe_studio.plugins.manuscript.ui.editor.text_bridge import (
    extract_document,
    load_into_document,
    paragraph_style_block_format,
    paragraph_style_char_format,
)
from skrybe_studio.plugins.manuscript.ui.editor.typewriter import target_scroll_value

if TYPE_CHECKING:
    from skrybe_studio.plugins.manuscript.plugin import ManuscriptPlugin

logger = logging.getLogger(__name__)

AUTOSAVE_DELAY_MS = 800

_STYLE_ITEMS = (
    (BlockKind.PARAGRAPH, "Normal"),
    (BlockKind.HEADING, "Heading"),
    (BlockKind.BLOCKQUOTE, "Blockquote"),
)


class DocumentEditor(QWidget):
    """Displays and edits exactly one text-bearing manuscript node."""

    titleChanged = Signal(str)

    def __init__(self, plugin: ManuscriptPlugin, node_id: UUID) -> None:
        super().__init__()
        self._plugin = plugin
        self._node_id = node_id
        self._loading = False
        self._dirty = False
        self.typewriter_enabled = False

        self._bold_button = QToolButton()
        self._bold_button.setText("B")
        self._bold_button.setCheckable(True)
        self._bold_button.clicked.connect(self._toggle_bold)
        self._italic_button = QToolButton()
        self._italic_button.setText("I")
        self._italic_button.setCheckable(True)
        self._italic_button.clicked.connect(self._toggle_italic)
        self._underline_button = QToolButton()
        self._underline_button.setText("U")
        self._underline_button.setCheckable(True)
        self._underline_button.clicked.connect(self._toggle_underline)

        self._style_combo = QComboBox()
        for kind, label in _STYLE_ITEMS:
            self._style_combo.addItem(label, kind)
        self._style_combo.currentIndexChanged.connect(self._apply_paragraph_style)

        find_button = QPushButton("Find/Replace")
        find_button.clicked.connect(self._toggle_find_bar)
        zoom_out_button = QPushButton("A-")
        zoom_out_button.clicked.connect(self._zoom_out)
        zoom_in_button = QPushButton("A+")
        zoom_in_button.clicked.connect(self._zoom_in)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self._bold_button)
        toolbar.addWidget(self._italic_button)
        toolbar.addWidget(self._underline_button)
        toolbar.addWidget(self._style_combo)
        toolbar.addStretch(1)
        toolbar.addWidget(find_button)
        toolbar.addWidget(zoom_out_button)
        toolbar.addWidget(zoom_in_button)

        self._text_edit = QTextEdit()
        self._text_edit.setAcceptRichText(False)
        self._text_edit.textChanged.connect(self._on_text_changed)
        self._text_edit.cursorPositionChanged.connect(self._on_cursor_position_changed)
        self._text_edit.selectionChanged.connect(self._update_word_count_label)

        self._find_bar = self._build_find_bar()
        self._find_bar.setVisible(False)

        self._word_count_label = QLabel("0 words")
        self._word_count_label.setObjectName("muted")
        self._dirty_label = QLabel("Saved")
        self._dirty_label.setObjectName("muted")

        status_row = QHBoxLayout()
        status_row.addWidget(self._word_count_label)
        status_row.addStretch(1)
        status_row.addWidget(self._dirty_label)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(self._find_bar)
        layout.addWidget(self._text_edit, stretch=1)
        layout.addLayout(status_row)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(AUTOSAVE_DELAY_MS)
        self._autosave_timer.timeout.connect(self._save)

        self._apply_zoom(self._plugin.get_editor_point_size())
        self._load()

    @property
    def node_id(self) -> UUID:
        return self._node_id

    # --- loading / saving --------------------------------------------------------

    def _load(self) -> None:
        if self._plugin.documents is None:
            return
        self._loading = True
        content = self._plugin.documents.load_content(self._node_id)
        load_into_document(self._text_edit.document(), content)
        self._loading = False
        self._dirty = False
        self._update_word_count_label()
        self._update_dirty_label()
        node = self._plugin.hierarchy.get_node(self._node_id) if self._plugin.hierarchy else None
        if node is not None:
            self.titleChanged.emit(node.title)

    def flush(self) -> None:
        """Immediately persists pending changes, bypassing the autosave debounce.
        Called when switching documents, closing the project, or shutting down."""
        if self._dirty:
            self._save()

    def _on_text_changed(self) -> None:
        if self._loading:
            return
        self._dirty = True
        self._update_dirty_label()
        self._update_word_count_label()
        self._autosave_timer.start()

    def _save(self) -> None:
        self._autosave_timer.stop()
        if not self._dirty or self._plugin.documents is None:
            return
        content = extract_document(self._text_edit.document())
        try:
            self._plugin.documents.save_content(self._node_id, content)
        except Exception:
            logger.exception("Autosave failed for manuscript node %s", self._node_id)
            self._dirty_label.setText("Autosave failed - changes not saved")
            self._dirty_label.setObjectName("error")
            self._dirty_label.style().unpolish(self._dirty_label)
            self._dirty_label.style().polish(self._dirty_label)
            return
        self._dirty = False
        self._update_dirty_label()

    def _update_dirty_label(self) -> None:
        self._dirty_label.setObjectName("muted")
        self._dirty_label.style().unpolish(self._dirty_label)
        self._dirty_label.style().polish(self._dirty_label)
        self._dirty_label.setText("Unsaved changes…" if self._dirty else "Saved")

    def _update_word_count_label(self) -> None:
        total = count_words(self._text_edit.toPlainText())
        cursor = self._text_edit.textCursor()
        if cursor.hasSelection():
            selected = count_words(cursor.selectedText())
            self._word_count_label.setText(f"{total} words   ({selected} selected)")
        else:
            self._word_count_label.setText(f"{total} words")

    # --- formatting ----------------------------------------------------------------

    def _toggle_bold(self) -> None:
        fmt = QTextCharFormat()
        is_bold = self._text_edit.fontWeight() > QFont.Weight.Normal
        fmt.setFontWeight(QFont.Weight.Normal if is_bold else QFont.Weight.Bold)
        self._text_edit.mergeCurrentCharFormat(fmt)

    def _toggle_italic(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self._text_edit.fontItalic())
        self._text_edit.mergeCurrentCharFormat(fmt)

    def _toggle_underline(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self._text_edit.fontUnderline())
        self._text_edit.mergeCurrentCharFormat(fmt)

    def _apply_paragraph_style(self, index: int) -> None:
        if self._loading or index < 0:
            return
        kind = self._style_combo.itemData(index)
        cursor = self._text_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        cursor.setBlockFormat(paragraph_style_block_format(kind))
        cursor.setCharFormat(paragraph_style_char_format(kind))
        self._text_edit.setTextCursor(cursor)

    # --- zoom -----------------------------------------------------------------------

    def _zoom_in(self) -> None:
        self._apply_zoom(self._plugin.get_editor_point_size() + 1)

    def _zoom_out(self) -> None:
        self._apply_zoom(max(6, self._plugin.get_editor_point_size() - 1))

    def _apply_zoom(self, point_size: float) -> None:
        font = self._text_edit.font()
        font.setPointSizeF(point_size)
        self._text_edit.setFont(font)
        self._plugin.set_editor_point_size(point_size)

    # --- typewriter scrolling --------------------------------------------------------

    def _on_cursor_position_changed(self) -> None:
        self._update_word_count_label()
        if self.typewriter_enabled:
            scrollbar = self._text_edit.verticalScrollBar()
            cursor_top = self._text_edit.cursorRect().top()
            viewport_height = self._text_edit.viewport().height()
            new_value = target_scroll_value(scrollbar.value(), cursor_top, viewport_height)
            if abs(new_value - scrollbar.value()) > 1:
                scrollbar.setValue(new_value)

    def set_typewriter_enabled(self, enabled: bool) -> None:
        self.typewriter_enabled = enabled

    # --- find / replace --------------------------------------------------------------

    def _build_find_bar(self) -> QWidget:
        bar = QWidget()
        self._find_edit = QLineEdit()
        self._find_edit.setPlaceholderText("Find…")
        self._replace_edit = QLineEdit()
        self._replace_edit.setPlaceholderText("Replace with…")
        next_button = QPushButton("Next")
        next_button.clicked.connect(lambda: self._find(backward=False))
        previous_button = QPushButton("Previous")
        previous_button.clicked.connect(lambda: self._find(backward=True))
        replace_button = QPushButton("Replace")
        replace_button.clicked.connect(self._replace_current)
        replace_all_button = QPushButton("Replace All")
        replace_all_button.clicked.connect(self._replace_all)
        close_button = QPushButton("Close")
        close_button.clicked.connect(lambda: self._find_bar.setVisible(False))

        row = QHBoxLayout(bar)
        row.addWidget(self._find_edit)
        row.addWidget(next_button)
        row.addWidget(previous_button)
        row.addWidget(self._replace_edit)
        row.addWidget(replace_button)
        row.addWidget(replace_all_button)
        row.addWidget(close_button)
        return bar

    def _toggle_find_bar(self) -> None:
        self._find_bar.setVisible(not self._find_bar.isVisible())
        if self._find_bar.isVisible():
            self._find_edit.setFocus()

    def show_find_bar(self) -> None:
        self._find_bar.setVisible(True)
        self._find_edit.setFocus()

    def _find(self, *, backward: bool) -> bool:
        query = self._find_edit.text()
        if not query:
            return False
        flags = QTextDocument.FindFlag.FindBackward if backward else QTextDocument.FindFlag(0)
        found = self._text_edit.find(query, flags)
        if not found:
            cursor = self._text_edit.textCursor()
            cursor.movePosition(
                QTextCursor.MoveOperation.End if backward else QTextCursor.MoveOperation.Start
            )
            self._text_edit.setTextCursor(cursor)
            found = self._text_edit.find(query, flags)
        return found

    def _replace_current(self) -> None:
        cursor = self._text_edit.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self._find_edit.text():
            cursor.insertText(self._replace_edit.text())
        self._find(backward=False)

    def _replace_all(self) -> None:
        query = self._find_edit.text()
        replacement = self._replace_edit.text()
        if not query:
            return
        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self._text_edit.setTextCursor(cursor)
        count = 0
        while self._text_edit.find(query):
            self._text_edit.textCursor().insertText(replacement)
            count += 1
        logger.debug("Replaced %d occurrence(s) of %r", count, query)
