"""Local manuscript templates: hierarchy only, no writing-methodology engine.

Each template is a plain nested description the hierarchy service turns
into real nodes. Adding a template means adding one function here - it
never touches persistence directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType


class ManuscriptTemplate(StrEnum):
    BLANK = "blank"
    THREE_ACT_NOVEL = "three_act_novel"
    SHORT_STORY = "short_story"
    NONFICTION_BOOK = "nonfiction_book"


@dataclass(frozen=True, slots=True)
class TemplateNode:
    node_type: ManuscriptNodeType
    title: str
    children: tuple[TemplateNode, ...] = ()


TEMPLATE_LABELS: dict[ManuscriptTemplate, str] = {
    ManuscriptTemplate.BLANK: "Blank Novel",
    ManuscriptTemplate.THREE_ACT_NOVEL: "Three-Act Novel",
    ManuscriptTemplate.SHORT_STORY: "Short Story",
    ManuscriptTemplate.NONFICTION_BOOK: "Nonfiction Book",
}


def _scene(title: str) -> TemplateNode:
    return TemplateNode(node_type=ManuscriptNodeType.SCENE, title=title)


def _chapter(title: str, *scenes: str) -> TemplateNode:
    return TemplateNode(
        node_type=ManuscriptNodeType.CHAPTER,
        title=title,
        children=tuple(_scene(s) for s in scenes),
    )


def template_structure(template: ManuscriptTemplate) -> tuple[TemplateNode, ...]:
    """The template's top-level children (directly under the manuscript root)."""
    if template == ManuscriptTemplate.BLANK:
        return ()
    if template == ManuscriptTemplate.THREE_ACT_NOVEL:
        return (
            TemplateNode(
                node_type=ManuscriptNodeType.PART,
                title="Act One",
                children=(_chapter("Chapter One", "Scene One"),),
            ),
            TemplateNode(
                node_type=ManuscriptNodeType.PART,
                title="Act Two",
                children=(_chapter("Chapter Two", "Scene One"),),
            ),
            TemplateNode(
                node_type=ManuscriptNodeType.PART,
                title="Act Three",
                children=(_chapter("Chapter Three", "Scene One"),),
            ),
        )
    if template == ManuscriptTemplate.SHORT_STORY:
        return (_scene("Opening"), _scene("Middle"), _scene("Ending"))
    if template == ManuscriptTemplate.NONFICTION_BOOK:
        return (
            TemplateNode(node_type=ManuscriptNodeType.DOCUMENT, title="Introduction"),
            _chapter("Chapter One"),
            _chapter("Chapter Two"),
            TemplateNode(node_type=ManuscriptNodeType.DOCUMENT, title="Conclusion"),
        )
    return ()
