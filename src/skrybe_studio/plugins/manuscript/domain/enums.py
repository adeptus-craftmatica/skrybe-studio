"""Manuscript node types and status vocabulary."""

from __future__ import annotations

from enum import StrEnum


class ManuscriptNodeType(StrEnum):
    MANUSCRIPT = "manuscript"
    FOLDER = "folder"
    PART = "part"
    CHAPTER = "chapter"
    SCENE = "scene"
    DOCUMENT = "document"


# Text-bearing node types own document content (see domain/document_ir.py).
# Everything else is a pure container: it may have a synopsis, but no body.
TEXT_BEARING_NODE_TYPES = frozenset({ManuscriptNodeType.SCENE, ManuscriptNodeType.DOCUMENT})

# Which child types each parent type may directly contain. MANUSCRIPT (the
# root) has no entry here - it is never itself a child of anything.
ALLOWED_CHILD_TYPES: dict[ManuscriptNodeType, frozenset[ManuscriptNodeType]] = {
    ManuscriptNodeType.MANUSCRIPT: frozenset(
        {
            ManuscriptNodeType.FOLDER,
            ManuscriptNodeType.PART,
            ManuscriptNodeType.CHAPTER,
            ManuscriptNodeType.SCENE,
            ManuscriptNodeType.DOCUMENT,
        }
    ),
    ManuscriptNodeType.FOLDER: frozenset(
        {
            ManuscriptNodeType.FOLDER,
            ManuscriptNodeType.PART,
            ManuscriptNodeType.CHAPTER,
            ManuscriptNodeType.SCENE,
            ManuscriptNodeType.DOCUMENT,
        }
    ),
    ManuscriptNodeType.PART: frozenset(
        {
            ManuscriptNodeType.FOLDER,
            ManuscriptNodeType.CHAPTER,
            ManuscriptNodeType.SCENE,
            ManuscriptNodeType.DOCUMENT,
        }
    ),
    ManuscriptNodeType.CHAPTER: frozenset(
        {
            ManuscriptNodeType.FOLDER,
            ManuscriptNodeType.SCENE,
            ManuscriptNodeType.DOCUMENT,
        }
    ),
    ManuscriptNodeType.SCENE: frozenset(),
    ManuscriptNodeType.DOCUMENT: frozenset(),
}


class NodeStatus(StrEnum):
    """Content-progress marker. Soft deletion/archival is tracked separately
    via `ManuscriptNode.archived_at` - this is not an "Archived" status."""

    PLANNED = "planned"
    DRAFT = "draft"
    REVISED = "revised"
    FINAL = "final"
