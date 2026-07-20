"""Markdown exporter: the compile IR walked into a single `.md` file.

Bold/italic spans map to standard Markdown (`**bold**`, `*italic*`);
underline has no standard Markdown equivalent and is dropped - a
documented limitation, not a bug (see `docs/manuscript-plugin.md`).
"""

from __future__ import annotations

from pathlib import Path

from skrybe_studio.plugins.manuscript.application.export.compile import (
    CompileDocument,
    CompileSection,
)
from skrybe_studio.plugins.manuscript.domain.document_ir import DocumentBlock, TextSpan
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType

SCENE_SEPARATOR = "* * *"
_MAX_HEADING_LEVEL = 6


def export_markdown(document: CompileDocument, output_path: Path) -> Path:
    lines: list[str] = [f"# {document.title}", ""]
    _walk(document.sections, lines)
    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return output_path


def _walk(sections: tuple[CompileSection, ...], lines: list[str]) -> None:
    previous_was_text = False
    for section in sections:
        is_text = section.node_type in (ManuscriptNodeType.SCENE, ManuscriptNodeType.DOCUMENT)
        if is_text:
            if previous_was_text:
                lines.append("")
                lines.append(SCENE_SEPARATOR)
            lines.append("")
            for block in section.blocks:
                rendered = _render_block(block)
                if rendered:
                    lines.append(rendered)
                    lines.append("")
        else:
            heading_level = min(section.level + 1, _MAX_HEADING_LEVEL)
            lines.append("")
            lines.append(f"{'#' * heading_level} {section.title}")
            _walk(section.children, lines)
        previous_was_text = is_text


def _render_block(block: DocumentBlock) -> str:
    text = "".join(_render_span(span) for span in block.spans)
    if block.kind.value == "blockquote":
        return f"> {text}"
    if block.kind.value == "list_item":
        return f"- {text}"
    return text


def _render_span(span: TextSpan) -> str:
    text = span.text
    if span.bold:
        text = f"**{text}**"
    if span.italic:
        text = f"*{text}*"
    return text
