"""Plain-text exporter: the compile IR walked into a single `.txt` file."""

from __future__ import annotations

from pathlib import Path

from skrybe_studio.plugins.manuscript.application.export.compile import (
    CompileDocument,
    CompileSection,
)
from skrybe_studio.plugins.manuscript.domain.document_ir import document_plain_text
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType

SCENE_SEPARATOR = "* * *"


def export_plain_text(document: CompileDocument, output_path: Path) -> Path:
    lines: list[str] = [document.title, ""]
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
            text = document_plain_text(section.blocks)
            if text:
                lines.append(text)
        else:
            lines.append("")
            lines.append(section.title)
            _walk(section.children, lines)
        previous_was_text = is_text
