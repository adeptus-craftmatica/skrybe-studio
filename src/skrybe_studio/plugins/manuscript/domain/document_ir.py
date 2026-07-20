"""The manuscript document intermediate representation (IR).

**Deliberate v0.2 content model decision** (see `docs/manuscript-plugin.md`
for the full rationale): rather than storing raw HTML or a plain string,
a text-bearing node's content is a small, Qt-free, JSON-serializable
sequence of `DocumentBlock`s. Each block has a `kind` (paragraph,
heading, blockquote, list item) and a tuple of `TextSpan`s (a run of text
plus bold/italic/underline flags).

This is not "an elaborate custom text engine" - it is flat, has no
markup, and cannot express arbitrary active content, so there is nothing
to sanitize. It is also the *same* representation the editor bridges to
a `QTextDocument` and every exporter (plain text, Markdown, HTML, DOCX)
walks - one source of truth instead of parsing HTML back out of the
editor for each destination format.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class BlockKind(StrEnum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    BLOCKQUOTE = "blockquote"
    LIST_ITEM = "list_item"
    SCENE_BREAK = "scene_break"


@dataclass(frozen=True, slots=True)
class TextSpan:
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False


@dataclass(frozen=True, slots=True)
class DocumentBlock:
    kind: BlockKind = BlockKind.PARAGRAPH
    spans: tuple[TextSpan, ...] = field(default_factory=tuple)
    # Heading level (1-3) when kind is HEADING; unused otherwise.
    level: int = 1

    @property
    def plain_text(self) -> str:
        return "".join(span.text for span in self.spans)


DocumentContent = tuple[DocumentBlock, ...]

EMPTY_DOCUMENT: DocumentContent = ()


def document_plain_text(blocks: DocumentContent) -> str:
    """Joins every block's text with newlines - the canonical plain-text view
    used for word counting, search indexing, and plain-text export."""
    return "\n".join(block.plain_text for block in blocks)


def paragraph(text: str) -> DocumentBlock:
    """Convenience constructor for a single unformatted paragraph block."""
    return DocumentBlock(kind=BlockKind.PARAGRAPH, spans=(TextSpan(text=text),) if text else ())


def plain_text_to_document(text: str) -> DocumentContent:
    """Fallback/import path: one paragraph block per blank-line-separated chunk."""
    if not text.strip():
        return EMPTY_DOCUMENT
    chunks = [chunk.strip("\n") for chunk in text.replace("\r\n", "\n").split("\n\n")]
    return tuple(paragraph(chunk) for chunk in chunks if chunk.strip())


def _span_to_dict(span: TextSpan) -> dict[str, Any]:
    data: dict[str, Any] = {"text": span.text}
    if span.bold:
        data["bold"] = True
    if span.italic:
        data["italic"] = True
    if span.underline:
        data["underline"] = True
    return data


def _span_from_dict(data: dict[str, Any]) -> TextSpan:
    return TextSpan(
        text=data.get("text", ""),
        bold=bool(data.get("bold", False)),
        italic=bool(data.get("italic", False)),
        underline=bool(data.get("underline", False)),
    )


def _block_to_dict(block: DocumentBlock) -> dict[str, Any]:
    data: dict[str, Any] = {
        "kind": block.kind.value,
        "spans": [_span_to_dict(span) for span in block.spans],
    }
    if block.kind == BlockKind.HEADING:
        data["level"] = block.level
    return data


def _block_from_dict(data: dict[str, Any]) -> DocumentBlock:
    return DocumentBlock(
        kind=BlockKind(data.get("kind", BlockKind.PARAGRAPH.value)),
        spans=tuple(_span_from_dict(span) for span in data.get("spans", [])),
        level=int(data.get("level", 1)),
    )


def serialize_document(blocks: DocumentContent) -> str:
    return json.dumps([_block_to_dict(block) for block in blocks])


def deserialize_document(raw: str | None) -> DocumentContent:
    if not raw:
        return EMPTY_DOCUMENT
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return EMPTY_DOCUMENT
    if not isinstance(data, list):
        return EMPTY_DOCUMENT
    return tuple(_block_from_dict(item) for item in data if isinstance(item, dict))


def blocks_from_iterable(blocks: Iterable[DocumentBlock]) -> DocumentContent:
    return tuple(blocks)
