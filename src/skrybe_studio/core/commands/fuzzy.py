"""Lightweight, dependency-free fuzzy matching for the command palette.

Ordered-subsequence matching (every needle character must appear in the
haystack in order, but not necessarily contiguously) with a score that
favors contiguous runs, word-boundary starts, and earlier matches - the
same signals users expect from editor command palettes, without pulling
in a fuzzy-matching dependency for this one dialog.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FuzzyMatch:
    matched: bool
    score: float


_NO_MATCH = FuzzyMatch(matched=False, score=0.0)


def fuzzy_match(needle: str, haystack: str) -> FuzzyMatch:
    """Score `haystack` against `needle` as an ordered subsequence match.

    An empty needle matches everything with a score of 0. Higher scores
    are better matches; scores are only comparable across calls with the
    same needle.
    """
    if not needle:
        return FuzzyMatch(matched=True, score=0.0)

    needle_lower = needle.lower()
    haystack_lower = haystack.lower()

    score = 0.0
    search_from = 0
    consecutive_run = 0
    first_match_index: int | None = None

    for char in needle_lower:
        found_index = haystack_lower.find(char, search_from)
        if found_index == -1:
            return _NO_MATCH

        if first_match_index is None:
            first_match_index = found_index

        if found_index == search_from:
            consecutive_run += 1
            score += 3 + consecutive_run
        else:
            consecutive_run = 0
            score += 1

        is_word_start = found_index == 0 or not haystack[found_index - 1].isalnum()
        if is_word_start:
            score += 2

        search_from = found_index + 1

    assert first_match_index is not None
    score -= first_match_index * 0.1
    score -= max(len(haystack) - len(needle), 0) * 0.05
    return FuzzyMatch(matched=True, score=score)
