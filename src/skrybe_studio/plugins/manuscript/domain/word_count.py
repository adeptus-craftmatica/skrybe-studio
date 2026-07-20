"""Word- and character-counting rules.

There is no single universally correct definition of "a word" across
languages and styles. This picks one deterministic, documented rule and
keeps it isolated here so it can be replaced without touching callers:

A word is any whitespace-separated token that contains at least one
Unicode "word" character (letter, digit, or underscore). Tokens made
entirely of punctuation - e.g. a lone "--" or "***" used as a scene-break
marker - are not counted. Contractions and hyphenated compounds
("don't", "well-worn") count as one word each, matching common writing
tools' behavior.
"""

from __future__ import annotations

import re

from skrybe_studio.plugins.manuscript.domain.document_ir import DocumentContent, document_plain_text

_PUNCTUATION_ONLY = re.compile(r"^[^\w]+$", re.UNICODE)


def count_words(text: str) -> int:
    return sum(1 for token in text.split() if not _PUNCTUATION_ONLY.match(token))


def count_characters(text: str, *, include_whitespace: bool = True) -> int:
    if include_whitespace:
        return len(text)
    return len("".join(text.split()))


def count_words_in_document(blocks: DocumentContent) -> int:
    return count_words(document_plain_text(blocks))
