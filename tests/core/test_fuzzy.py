from __future__ import annotations

from skrybe_studio.core.commands.fuzzy import fuzzy_match


def test_empty_needle_matches_everything_with_zero_score() -> None:
    result = fuzzy_match("", "Anything")

    assert result.matched is True
    assert result.score == 0.0


def test_out_of_order_characters_do_not_match() -> None:
    assert fuzzy_match("ba", "abc").matched is False


def test_missing_character_does_not_match() -> None:
    assert fuzzy_match("xyz", "abc").matched is False


def test_case_insensitive_matching() -> None:
    assert fuzzy_match("NOTE", "New Note").matched is True


def test_contiguous_match_scores_higher_than_scattered() -> None:
    contiguous = fuzzy_match("note", "New Note")
    scattered = fuzzy_match("note", "N o t campaigns e")

    assert contiguous.matched is True
    assert scattered.matched is True
    assert contiguous.score > scattered.score


def test_word_boundary_match_scores_higher_than_mid_word() -> None:
    boundary = fuzzy_match("new", "New Note")
    mid_word = fuzzy_match("ew", "New Note")

    assert boundary.score > mid_word.score


def test_earlier_match_scores_higher_than_later_match() -> None:
    early = fuzzy_match("open", "Open Manuscript")
    late = fuzzy_match("open", "Reopen Manuscript")

    assert early.score > late.score


def test_shorter_haystack_scores_higher_for_equal_quality_match() -> None:
    short = fuzzy_match("open", "Open")
    long = fuzzy_match("open", "Open the current manuscript in a new window")

    assert short.score > long.score
