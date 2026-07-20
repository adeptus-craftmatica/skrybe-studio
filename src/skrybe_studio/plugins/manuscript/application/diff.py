"""A basic line-level diff for comparing a snapshot against the current document.

Uses the standard library's `difflib` - no Git dependency, and no attempt
at anything more sophisticated than line-level equal/insert/delete.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from enum import StrEnum


class DiffLineKind(StrEnum):
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"


@dataclass(frozen=True, slots=True)
class DiffLine:
    kind: DiffLineKind
    text: str


_PREFIX_TO_KIND = {
    "  ": DiffLineKind.EQUAL,
    "+ ": DiffLineKind.INSERT,
    "- ": DiffLineKind.DELETE,
}


def diff_lines(old_text: str, new_text: str) -> list[DiffLine]:
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    result: list[DiffLine] = []
    for line in difflib.ndiff(old_lines, new_lines):
        prefix, text = line[:2], line[2:]
        kind = _PREFIX_TO_KIND.get(prefix)
        if kind is None:  # "? " intraline hint markers - not surfaced
            continue
        result.append(DiffLine(kind=kind, text=text))
    return result
