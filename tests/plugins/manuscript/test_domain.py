from __future__ import annotations

from uuid import uuid4

import pytest

from skrybe_studio.plugins.manuscript.domain.document_ir import (
    BlockKind,
    DocumentBlock,
    TextSpan,
    deserialize_document,
    document_plain_text,
    plain_text_to_document,
    serialize_document,
)
from skrybe_studio.plugins.manuscript.domain.enums import ManuscriptNodeType
from skrybe_studio.plugins.manuscript.domain.exceptions import (
    CyclicHierarchyError,
    InvalidHierarchyError,
)
from skrybe_studio.plugins.manuscript.domain.models import (
    entity_type_for,
    raise_if_cyclic,
    validate_child_type,
    would_create_cycle,
)
from skrybe_studio.plugins.manuscript.domain.word_count import count_characters, count_words


@pytest.mark.parametrize(
    ("parent_type", "child_type"),
    [
        (ManuscriptNodeType.MANUSCRIPT, ManuscriptNodeType.PART),
        (ManuscriptNodeType.MANUSCRIPT, ManuscriptNodeType.CHAPTER),
        (ManuscriptNodeType.MANUSCRIPT, ManuscriptNodeType.SCENE),
        (ManuscriptNodeType.PART, ManuscriptNodeType.CHAPTER),
        (ManuscriptNodeType.PART, ManuscriptNodeType.SCENE),
        (ManuscriptNodeType.CHAPTER, ManuscriptNodeType.SCENE),
        (ManuscriptNodeType.CHAPTER, ManuscriptNodeType.DOCUMENT),
        (ManuscriptNodeType.FOLDER, ManuscriptNodeType.CHAPTER),
    ],
)
def test_valid_parent_child_relationships_are_accepted(parent_type, child_type) -> None:
    validate_child_type(parent_type, child_type)  # must not raise


@pytest.mark.parametrize(
    ("parent_type", "child_type"),
    [
        (ManuscriptNodeType.PART, ManuscriptNodeType.PART),
        (ManuscriptNodeType.CHAPTER, ManuscriptNodeType.CHAPTER),
        (ManuscriptNodeType.CHAPTER, ManuscriptNodeType.PART),
        (ManuscriptNodeType.SCENE, ManuscriptNodeType.SCENE),
        (ManuscriptNodeType.SCENE, ManuscriptNodeType.DOCUMENT),
        (ManuscriptNodeType.DOCUMENT, ManuscriptNodeType.SCENE),
        (ManuscriptNodeType.PART, ManuscriptNodeType.MANUSCRIPT),
    ],
)
def test_invalid_parent_child_relationships_are_rejected(parent_type, child_type) -> None:
    with pytest.raises(InvalidHierarchyError):
        validate_child_type(parent_type, child_type)


def test_entity_type_mapping_uses_manuscript_project_for_root() -> None:
    assert entity_type_for(ManuscriptNodeType.MANUSCRIPT) == "manuscript.project"
    assert entity_type_for(ManuscriptNodeType.SCENE) == "manuscript.scene"
    assert entity_type_for(ManuscriptNodeType.CHAPTER) == "manuscript.chapter"


def test_would_create_cycle_detects_self_parenting() -> None:
    node_id = uuid4()
    assert would_create_cycle(node_id, node_id, lambda _id: None) is True


def test_would_create_cycle_detects_descendant_becoming_ancestor() -> None:
    root, chapter, scene = uuid4(), uuid4(), uuid4()
    parents = {chapter: root, scene: chapter, root: None}

    # Moving `root` under `scene` (a descendant of root) would create a cycle.
    assert would_create_cycle(root, scene, parents.get) is True


def test_would_create_cycle_allows_unrelated_move() -> None:
    part_a, part_b, chapter = uuid4(), uuid4(), uuid4()
    parents = {chapter: part_a, part_a: None, part_b: None}

    assert would_create_cycle(chapter, part_b, parents.get) is False


def test_raise_if_cyclic_raises_for_a_real_cycle() -> None:
    root, scene = uuid4(), uuid4()
    parents = {scene: root, root: None}
    with pytest.raises(CyclicHierarchyError):
        raise_if_cyclic(root, scene, parents.get)


def test_count_words_ignores_punctuation_only_tokens() -> None:
    assert count_words("Hello, world! -- ***") == 2


def test_count_words_counts_contractions_and_hyphenated_words_once() -> None:
    assert count_words("don't stop well-worn paths") == 4


def test_count_words_handles_unicode_letters() -> None:
    assert count_words("café naïve résumé") == 3


def test_count_characters_with_and_without_whitespace() -> None:
    assert count_characters("a b c") == 5
    assert count_characters("a b c", include_whitespace=False) == 3


def test_document_ir_round_trips_through_json() -> None:
    blocks = (
        DocumentBlock(
            kind=BlockKind.HEADING,
            spans=(TextSpan(text="Chapter One"),),
            level=1,
        ),
        DocumentBlock(
            kind=BlockKind.PARAGRAPH,
            spans=(
                TextSpan(text="It was "),
                TextSpan(text="dark", italic=True),
                TextSpan(text="."),
            ),
        ),
    )

    serialized = serialize_document(blocks)
    restored = deserialize_document(serialized)

    assert restored == blocks


def test_deserialize_document_handles_empty_and_invalid_input() -> None:
    assert deserialize_document(None) == ()
    assert deserialize_document("") == ()
    assert deserialize_document("not json") == ()
    assert deserialize_document("[]") == ()


def test_document_plain_text_joins_blocks_with_newlines() -> None:
    blocks = (
        DocumentBlock(spans=(TextSpan(text="First paragraph"),)),
        DocumentBlock(spans=(TextSpan(text="Second paragraph"),)),
    )
    assert document_plain_text(blocks) == "First paragraph\nSecond paragraph"


def test_plain_text_to_document_splits_on_blank_lines() -> None:
    blocks = plain_text_to_document("Paragraph one.\n\nParagraph two.")
    assert [block.plain_text for block in blocks] == ["Paragraph one.", "Paragraph two."]


def test_plain_text_to_document_empty_string_yields_no_blocks() -> None:
    assert plain_text_to_document("   ") == ()
