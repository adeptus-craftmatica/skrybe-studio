"""Bridges the Qt-free document IR to Qt's `QTextDocument`/`QTextCursor`.

This is the only place the IR touches Qt - `domain/document_ir.py` stays
plain Python. The mapping is a deliberate, documented heuristic rather
than a lossless round-trip: a block is recognized as a HEADING or
BLOCKQUOTE by markers this module itself applies on load (a distinctive
left margin for blockquotes, bold+enlarged text for headings), then
detected again on extract by checking for those same markers. Content
this editor never creates (list items, scene breaks) is loaded as a
plain paragraph - a documented limitation, not a bug (see
`docs/manuscript-plugin.md`).
"""

from __future__ import annotations

from PySide6.QtGui import QFont, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextDocument

from skrybe_studio.plugins.manuscript.domain.document_ir import (
    BlockKind,
    DocumentBlock,
    DocumentContent,
    TextSpan,
)

BASE_POINT_SIZE = 13.0
HEADING_POINT_SIZE = BASE_POINT_SIZE + 4
BLOCKQUOTE_LEFT_MARGIN = 30.0


def paragraph_style_char_format(
    kind: BlockKind, *, base_point_size: float = BASE_POINT_SIZE
) -> QTextCharFormat:
    char_format = QTextCharFormat()
    if kind == BlockKind.HEADING:
        char_format.setFontWeight(QFont.Weight.Bold)
        char_format.setFontPointSize(base_point_size + 4)
    else:
        char_format.setFontWeight(QFont.Weight.Normal)
        char_format.setFontPointSize(base_point_size)
    return char_format


def paragraph_style_block_format(kind: BlockKind) -> QTextBlockFormat:
    block_format = QTextBlockFormat()
    if kind == BlockKind.BLOCKQUOTE:
        block_format.setLeftMargin(BLOCKQUOTE_LEFT_MARGIN)
    return block_format


def load_into_document(qt_document: QTextDocument, blocks: DocumentContent) -> None:
    qt_document.clear()
    cursor = QTextCursor(qt_document)
    for index, block in enumerate(blocks):
        if index > 0:
            cursor.insertBlock()
        cursor.setBlockFormat(paragraph_style_block_format(block.kind))
        base_format = paragraph_style_char_format(block.kind)
        for span in block.spans:
            char_format = QTextCharFormat(base_format)
            if span.bold:
                char_format.setFontWeight(QFont.Weight.Bold)
            if span.italic:
                char_format.setFontItalic(True)
            if span.underline:
                char_format.setFontUnderline(True)
            cursor.insertText(span.text, char_format)


def extract_document(qt_document: QTextDocument) -> DocumentContent:
    blocks: list[DocumentBlock] = []
    block = qt_document.begin()
    while block.isValid():
        spans: list[TextSpan] = []
        is_heading = False
        is_blockquote = block.blockFormat().leftMargin() >= BLOCKQUOTE_LEFT_MARGIN
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            if fragment.isValid() and fragment.text():
                char_format = fragment.charFormat()
                bold = char_format.fontWeight() > QFont.Weight.Normal
                if char_format.fontPointSize() >= HEADING_POINT_SIZE and bold:
                    is_heading = True
                spans.append(
                    TextSpan(
                        text=fragment.text(),
                        bold=bold and char_format.fontPointSize() < HEADING_POINT_SIZE,
                        italic=char_format.fontItalic(),
                        underline=char_format.fontUnderline(),
                    )
                )
            iterator += 1
        if spans:
            kind = (
                BlockKind.HEADING
                if is_heading
                else (BlockKind.BLOCKQUOTE if is_blockquote else BlockKind.PARAGRAPH)
            )
            blocks.append(DocumentBlock(kind=kind, spans=tuple(spans)))
        block = block.next()
    return tuple(blocks)
