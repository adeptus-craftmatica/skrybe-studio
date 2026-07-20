"""HTML exporter: the compile IR walked into a single, self-contained `.html` file.

Every span of user text is escaped via `html.escape` before being wrapped
in the (fixed, plugin-authored) markup - user content is never treated
as trusted HTML, so there is nothing to sanitize beyond standard escaping.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from skrybe_studio.plugins.manuscript.application.export.compile import (
    CompileDocument,
    CompileSection,
)
from skrybe_studio.plugins.manuscript.domain.document_ir import DocumentBlock, TextSpan
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType

_MAX_HEADING_LEVEL = 6

_STYLE = """
body { font-family: Georgia, 'Times New Roman', serif; max-width: 40em; margin: 2em auto; line-height: 1.6; }
h1, h2, h3, h4, h5, h6 { font-family: -apple-system, 'Segoe UI', sans-serif; }
hr.scene-break { border: none; text-align: center; margin: 2em 0; }
hr.scene-break::before { content: "* * *"; }
blockquote { border-left: 3px solid #ccc; margin-left: 0; padding-left: 1em; color: #555; }
"""


def export_html(document: CompileDocument, output_path: Path) -> Path:
    body: list[str] = [f"<h1>{escape(document.title)}</h1>"]
    _walk(document.sections, body)
    html_doc = (
        '<!doctype html>\n<html><head><meta charset="utf-8">'
        f"<title>{escape(document.title)}</title><style>{_STYLE}</style></head>"
        f"<body>\n{''.join(body)}\n</body></html>\n"
    )
    output_path.write_text(html_doc, encoding="utf-8")
    return output_path


def _walk(sections: tuple[CompileSection, ...], body: list[str]) -> None:
    previous_was_text = False
    for section in sections:
        is_text = section.node_type in (ManuscriptNodeType.SCENE, ManuscriptNodeType.DOCUMENT)
        if is_text:
            if previous_was_text:
                body.append('<hr class="scene-break">\n')
            for block in section.blocks:
                body.append(_render_block(block))
        else:
            heading_level = min(section.level + 1, _MAX_HEADING_LEVEL)
            body.append(f"<h{heading_level}>{escape(section.title)}</h{heading_level}>\n")
            _walk(section.children, body)
        previous_was_text = is_text


def _render_block(block: DocumentBlock) -> str:
    inner = "".join(_render_span(span) for span in block.spans)
    tag = {"blockquote": "blockquote", "list_item": "li"}.get(block.kind.value, "p")
    return f"<{tag}>{inner}</{tag}>\n"


def _render_span(span: TextSpan) -> str:
    text = escape(span.text)
    if span.bold:
        text = f"<strong>{text}</strong>"
    if span.italic:
        text = f"<em>{text}</em>"
    if span.underline:
        text = f"<u>{text}</u>"
    return text
